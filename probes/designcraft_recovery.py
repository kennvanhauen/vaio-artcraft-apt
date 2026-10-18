#!/usr/bin/env python3
"""Observe automatic idle recovery, crash only our disposable app, then reopen it."""
import json,os,socket,subprocess,time
from pathlib import Path
base=Path('/tmp/vaio-designcraft-test/recovery-'+str(os.getpid()));base.mkdir(parents=True)
binary=os.environ.get('VAIO_DESIGN_BINARY','/tmp/vaio-designcraft-test/designcraft')
env=dict(os.environ,DISPLAY=':0',DESIGNCRAFT_CONFIG_DIR=str(base/'profile'),DESIGNCRAFT_NO_PREFS='1',LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
result={'profile':str(base)};p=None;connection=None;serial=0

def start():
    global p,connection,channel
    connection=None;p=subprocess.Popen([binary,'--control','7994'],env=env,stdin=subprocess.DEVNULL,stdout=(base/'application.log').open('a'),stderr=subprocess.STDOUT)
    until=time.monotonic()+45
    while time.monotonic()<until:
        if p.poll() is not None:raise RuntimeError('Recovery GUI exited')
        try:connection=socket.create_connection(('127.0.0.1',7994),timeout=45);break
        except OSError:time.sleep(.2)
    assert connection;channel=connection.makefile('rwb',buffering=0)
def request(m,params=None):
    global serial
    serial+=1;channel.write((json.dumps({'id':serial,'method':m,'params':params or {}})+'\n').encode());r=json.loads(channel.readline().decode());assert r.get('ok'),r
    return r.get('result')
def execute(c,params=None):return request('engine.execute',{'command':c,'params':params or {}})
try:
    start();execute('file.new',{'width':420,'height':595,'title':'Original unsaved VAIO draft'})
    execute('frame.create',{'rect':[30,30,390,200],'content':'text','text':'Original unsaved DesignCraft draft','caret':False})
    request('ui.tool.select',{'tool':'selection'})
    # No control requests or keyboard/mouse activity during this idle interval.
    at=time.monotonic();until=at+48
    while time.monotonic()<until:
        copies=list((base/'profile'/'Recovery').rglob('*.designcraft'))
        if copies:break
        if p.poll() is not None:raise RuntimeError('GUI exited before recovery')
        time.sleep(1)
    result['automatic_copy_seconds']=round(time.monotonic()-at,2)
    assert copies,'No automatic recovery copy during 48 seconds of idle'
    p.kill();p.wait(timeout=10);connection.close();start()
    result['restored']=request('document.inspect')
    assert 'Original unsaved DesignCraft draft' in json.dumps(result['restored']) and result['restored']['dirty']
    request('app.save',{'path':str(base/'recovered.designcraft')});assert (base/'recovered.designcraft').exists()
    request('app.quit');p.wait(timeout=15);result['passed']=True
except Exception as e:result.update(passed=False,error=str(e))
finally:
    if p and p.poll() is None:p.terminate();p.wait(timeout=10)
    if connection:connection.close()
Path('/tmp/vaio-designcraft-test/recovery-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='restored'},indent=2))
raise SystemExit(0 if result.get('passed') else 1)
