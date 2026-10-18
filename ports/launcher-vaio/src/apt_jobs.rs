//! Coalesce Update All into one allowlisted native APT transaction.
use crate::apt::{self,ManagedApp};
use artcraft_launcher_core::protocol::{Event,JobPhase};
use std::collections::{HashSet,VecDeque};
use std::process::Command;
use std::sync::{Arc,Mutex,PoisonError,mpsc};
use std::time::Duration;

pub struct Queue {
    work:mpsc::Sender<(ManagedApp,bool)>,
    pending:Arc<Mutex<HashSet<&'static str>>>,
    events:mpsc::Sender<Event>,
    context:egui::Context,
}
impl Queue {
    pub fn new(events:mpsc::Sender<Event>,context:egui::Context)->Self {
        let (work,receiver)=mpsc::channel();
        let pending=Arc::new(Mutex::new(HashSet::new()));
        let e=events.clone();let c=context.clone();let p=pending.clone();
        std::thread::spawn(move ||worker(receiver,e,c,p));
        Self{work,pending,events,context}
    }
    pub fn enqueue(&self,app:ManagedApp,remove:bool){
        if !self.pending.lock().unwrap_or_else(PoisonError::into_inner).insert(app.id){return;}
        let _=self.events.send(Event::Progress{app:app.id.into(),phase:JobPhase::Waiting});
        if self.work.send((app,remove)).is_err(){
            self.pending.lock().unwrap_or_else(PoisonError::into_inner).remove(app.id);
            let _=self.events.send(Event::JobFinished{app:app.id.into(),result:Err("Package worker stopped. Restart the launcher and try again.".into())});
        }
        self.context.request_repaint();
    }
}
fn worker(receiver:mpsc::Receiver<(ManagedApp,bool)>,events:mpsc::Sender<Event>,context:egui::Context,pending:Arc<Mutex<HashSet<&'static str>>>){
    let mut backlog=VecDeque::new();
    loop {
        let first=match backlog.pop_front(){Some(job)=>job,None=>match receiver.recv(){Ok(job)=>job,Err(_)=>return}};
        let remove=first.1;let mut batch=vec![first.0];
        while batch.len()<apt::APPS.len(){
            match receiver.recv_timeout(Duration::from_millis(80)){
                Ok((app,action)) if action==remove=>batch.push(app),
                Ok(job)=>{backlog.push_back(job);break;},Err(_)=>break,
            }
        }
        let expected:Vec<_>=batch.iter().map(|app|apt::snapshot_for(app).ok()
            .and_then(|state|state.get("candidate").and_then(|v|v.as_str()).map(str::to_owned))).collect();
        for app in &batch{let _=events.send(Event::Progress{app:app.id.into(),phase:if remove{JobPhase::Removing}else{JobPhase::Installing}});}
        context.request_repaint();
        let action=if remove{"remove"}else{"install"};
        let packages=batch.iter().map(|app|app.package).collect::<Vec<_>>().join(" ");
        // Every interpolated word comes from the compile-time ManagedApp allowlist.
        let command=format!("/usr/bin/uxterm -T 'VAIO App Launcher - APT' -e /usr/lib/artcraft-launcher-vaio/apt-action {action} {packages}");
        let status=Command::new("/usr/bin/gksu").args(["-S","-m",
            "Use native APT for the selected VAIO previews. Review and confirm the package operation in the terminal.",&command]).status();
        let failure=match status{Ok(status) if status.success()=>None,Ok(_)=>Some("APT operation was cancelled or failed.".to_string()),Err(error)=>Some(error.to_string())};
        for (app,expected) in batch.iter().zip(expected.iter()){
            let result=apt::snapshot_for(app).and_then(|state|{
                let installed=state.get("installed").and_then(|v|v.as_str());
                let complete=if remove{installed.is_none()}else{installed.is_some_and(|actual|expected.as_deref().is_none_or(|candidate|
                    Command::new("/usr/bin/dpkg").args(["--compare-versions",actual,"ge",candidate]).status().is_ok_and(|status|status.success())))};
                if complete{Ok("APT operation completed".into())}else{Err(failure.clone().unwrap_or_else(||"The requested package change was not completed; check the APT terminal.".into()))}
            });
            pending.lock().unwrap_or_else(PoisonError::into_inner).remove(app.id);
            let _=events.send(Event::JobFinished{app:app.id.into(),result});
        }
        if let Ok(state)=apt::state_events(){for event in state{let _=events.send(event);}}
        context.request_repaint();
    }
}
