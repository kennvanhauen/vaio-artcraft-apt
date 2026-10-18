#!/usr/bin/env python3
"""Same executable, file and editing state; only the steady-caret flag changes."""
import json,os,socket,subprocess,time
from pathlib import Path
base=Path('/tmp/vaio-deckcraft-test/caret-comparison');base.mkdir(parents=True,exist_ok=True)
binary='/tmp/vaio-deckcraft-test/deckcraft';results=[]
for steady in ['0','1']:
    env=dict(os.environ,DISPLAY=':0',DECKCRAFT_NO_AUDIO='1',DECKCRAFT_NO_PREFS='1',DECKCRAFT_NO_RECOVERY='1',
             DECKCRAFT_STATIC_CARET=steady,XDG_CONFIG_HOME=str(base/steady),LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
    with (base/('app-'+steady+'.log')).open('w') as log:
        p=subprocess.Popen([binary,'--control','7993','/tmp/vaio-deckcraft-test/original.pptx'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        connection=None
        try:
            until=time.monotonic()+30
            while time.monotonic()<until:
                try:connection=socket.create_connection(('127.0.0.1',7993),timeout=30);break
                except OSError:time.sleep(.2)
            assert connection,'No own control connection'
            channel=connection.makefile('rwb',buffering=0);serial=0
            def request(method,params=None):
                global serial
                serial+=1;channel.write((json.dumps({'id':serial,'method':method,'params':params or {}})+'\n').encode())
                reply=json.loads(channel.readline().decode());assert reply.get('ok'),reply
                return reply.get('result')
            def execute(command,params=None):return request('engine.execute',{'command':command,'params':params or {}})
            request('ui.resize',{'width':1100,'height':650});execute('slide.go',{'index':0})
            shape=execute('insert.textBox',{'rect':[70,380,700,70],'text':'Same synthetic editing state'})
            execute('text.edit',{'id':shape['id'],'end':True});request('ui.inspect');time.sleep(2)
            def sample():
                f=Path('/proc/%d/stat'%p.pid).read_text().rsplit(')',1)[1].split();return int(f[11])+int(f[12])
            before=sample();at=time.monotonic();time.sleep(5);after=sample();duration=time.monotonic()-at
            results.append({'steady_caret':steady=='1','cpu_percent_one_logical_cpu':round(100*(after-before)/os.sysconf('SC_CLK_TCK')/duration,2)})
        finally:
            if connection:connection.close()
            p.terminate();p.wait(timeout=10)
result={'samples':results,'passed':len(results)==2 and results[1]['cpu_percent_one_logical_cpu']<5}
(base/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
