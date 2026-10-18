#!/usr/bin/env python3
"""Two-phase autosave check; respect the upstream five-minute recovery lease."""
import json,os,socket,subprocess,sys,time
from pathlib import Path
base=Path('/tmp/vaio-cadcraft-test');phase=base/'recovery-phase.json';binary=os.environ.get('VAIO_CAD_BINARY',str(base/'cadcraft'));mode=sys.argv[1] if len(sys.argv)>1 else 'snapshot'
r={};p=None;c=None;serial=0
profile=base/('recovery-'+str(os.getpid())) if mode=='snapshot' else Path(json.loads(phase.read_text())['profile'])
profile.mkdir(exist_ok=True)
env=dict(os.environ,DISPLAY=':0',CADCRAFT_CONFIG_DIR=str(profile),XDG_CONFIG_HOME=str(profile/'config'),XDG_DATA_HOME=str(profile/'data'),XDG_CACHE_HOME=str(profile/'cache'),LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
def start():
 global p,c,ch
 subprocess.run(['xscreensaver-command','-deactivate'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 p=subprocess.Popen([binary,'--control','7994'],env=env,stdin=subprocess.DEVNULL,stdout=(profile/'application.log').open('a'),stderr=subprocess.STDOUT)
 until=time.monotonic()+45
 while time.monotonic()<until:
  if p.poll() is not None:raise RuntimeError('Recovery GUI exited')
  try:c=socket.create_connection(('127.0.0.1',7994),timeout=60);break
  except OSError:time.sleep(.2)
 assert c;ch=c.makefile('rwb',buffering=0)
def req(m,a=None):
 global serial
 serial+=1;ch.write((json.dumps({'id':serial,'method':m,'params':a or {}})+'\n').encode());q=json.loads(ch.readline().decode());assert q.get('ok'),q
 return q.get('result')
def ex(n,a=None):return req('engine.execute',{'command':n,'params':a or {}})
try:
 if mode=='snapshot':
  start();ex('setvar',{'name':'SAVETIME','value':1});ex('text',{'at':[0,0],'height':5,'text':'Original unsaved CADCraft VAIO draft'})
  at=time.monotonic();copies=[]
  while time.monotonic()-at<78:
   copies=list((profile/'autosave').glob('*.sv$'))
   if copies:break
   if p.poll() is not None:raise RuntimeError('GUI exited before autosave')
   time.sleep(1)
  assert copies,'No automatic snapshot after 78 seconds without input'
  r={'profile':str(profile),'snapshot':str(copies[0]),'automatic_copy_seconds':round(time.monotonic()-at,2)}
  p.kill();p.wait(timeout=10);r['crashed_at']=time.time();r['recover_after']=max([x.stat().st_mtime for x in (profile/'autosave').glob('*.lock')]+[time.time()])+303
  phase.write_text(json.dumps(r,indent=2)+'\n');r['passed']=True
 elif mode=='restore':
  r=json.loads(phase.read_text());assert time.time()>=r['recover_after'],'Recovery lease has not expired yet'
  start();time.sleep(1);req('ui.screenshot',{'path':str(base/'recovery-offer.png')})
  # Open button observed in the inspected 1440x650 Drawing Recovery modal.
  req('ui.focus');req('ui.click',{'x':786,'y':320});r['recovery_ui_open_clicked']=True
  until=time.monotonic()+8
  while time.monotonic()<until:
   r['restored']=req('drawing.inspect',{'entities':True})
   if 'Original unsaved CADCraft VAIO draft' in json.dumps(r['restored']) and r['restored']['dirty']:break
   time.sleep(.25)
  assert 'Original unsaved CADCraft VAIO draft' in json.dumps(r['restored']) and r['restored']['dirty']
  req('app.save',{'path':str(profile/'recovered.dxf')});assert (profile/'recovered.dxf').exists()
  req('app.quit');p.wait(timeout=15);r['passed']=True;(base/'recovery-result.json').write_text(json.dumps(r,indent=2)+'\n')
 else:raise RuntimeError('Unknown recovery phase')
except Exception as e:
 r.update(passed=False,error=repr(e))
 (base/'recovery-ui-debug-result.json').write_text(json.dumps(r,indent=2)+'\n')
finally:
 if p and p.poll() is None:p.terminate();p.wait(timeout=10)
 if c:c.close()
print(json.dumps({k:v for k,v in r.items() if k!='restored'},indent=2));raise SystemExit(0 if r.get('passed') else 1)
