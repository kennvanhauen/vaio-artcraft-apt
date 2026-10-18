#!/usr/bin/env python3
"""Recover an original unsaved draft after killing only the owned test process."""
import json, os, socket, subprocess, time
from pathlib import Path
base=Path('/tmp/vaio-vectorcraft-test/recovery-check');base.mkdir(parents=True,exist_ok=True)
binary=os.environ.get('VAIO_VECTOR_BINARY','/tmp/vaio-vectorcraft-test/vectorcraft')
env=dict(os.environ,DISPLAY=':0',VECTORCRAFT_NO_PREFS='1',XDG_CONFIG_HOME=str(base/'config'),XDG_DATA_HOME=str(base/'data'),LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
result={};p=None;connection=None;serial=0
def start():
    global p,connection,channel
    p=subprocess.Popen([binary,'--control','7994','--automation-read-root',str(base),'--automation-write-root',str(base)],env=env,stdin=subprocess.DEVNULL,stdout=(base/'application.log').open('a'),stderr=subprocess.STDOUT)
    until=time.monotonic()+40
    while time.monotonic()<until:
        if p.poll() is not None:raise RuntimeError('Recovery GUI exited during startup')
        try:connection=socket.create_connection(('127.0.0.1',7994),timeout=45);break
        except OSError:time.sleep(.2)
    assert connection
    channel=connection.makefile('rwb',buffering=0)
def request(method,params=None):
    global serial
    serial+=1;channel.write((json.dumps({'id':serial,'method':method,'params':params or {}})+'\n').encode())
    reply=json.loads(channel.readline().decode());assert reply.get('ok'),reply
    return reply.get('result')
def execute(command,params=None):return request('engine.execute',{'command':command,'params':params or {}})
try:
    start()
    execute('prefs.set',{'values':{'autosaveRecovery':True,'autosaveInterval':1,'recoveryFolder':str(base/'store')}})
    execute('file.new',{'name':'Original recovery test','width':300,'height':200})
    execute('text.create',{'x':20,'y':50,'text':'Original unsaved VectorCraft draft','font':'Inter','size':14})
    at=time.monotonic();until=at+80
    while time.monotonic()<until:
        copies=list((base/'store').rglob('*.vectorcraft'))
        if copies:break
        if p.poll() is not None:raise RuntimeError('GUI exited before autosave')
        time.sleep(1)
    assert copies,'Automatic recovery copy not observed'
    result['automatic_copy_seconds']=round(time.monotonic()-at,2)
    # The subprocess and its isolated data folder were created by this probe.
    p.kill();p.wait(timeout=10);connection.close();connection=None
    start()
    execute('prefs.set',{'key':'recoveryFolder','value':str(base/'store')})
    result['available']=execute('file.recovery.list')
    assert result['available']['copies']
    result['restore']=execute('file.recovery.restore')
    assert result['restore']['restored'] and not result['restore']['failed']
    result['restored_document']=request('document.inspect',{'depth':3})
    assert 'Original unsaved VectorCraft draft' in json.dumps(result['restored_document'])
    assert result['restored_document']['dirty']
    request('app.save',{'path':str(base/'recovered.vectorcraft')})
    until=time.monotonic()+15
    while time.monotonic()<until:
        state=request('ui.inspect')
        if not state.get('background'):break
        time.sleep(.2)
    assert (base/'recovered.vectorcraft').exists()
    request('app.quit');p.wait(timeout=15)
    result['passed']=True
except Exception as error:result.update(passed=False,error=str(error))
finally:
    if p and p.poll() is None:p.terminate();p.wait(timeout=10)
    if connection:connection.close()
(base/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='restored_document'},indent=2))
raise SystemExit(0 if result.get('passed') else 1)
