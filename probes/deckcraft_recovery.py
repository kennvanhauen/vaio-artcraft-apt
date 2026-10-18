#!/usr/bin/env python3
"""Isolated close-cancel and idle AutoRecover/restart test; no user work touched."""
import json,os,socket,subprocess,time,zipfile
from pathlib import Path
base=Path('/tmp/vaio-deckcraft-test/recovery-'+str(int(time.time())));base.mkdir(parents=True,mode=0o700)
(base/'config/deckcraft').mkdir(parents=True)
(base/'config/deckcraft/prefs.json').write_text('{"recoveryMinutes":0.1}')
binary=os.environ.get('VAIO_DECK_BINARY','/tmp/vaio-deckcraft-test/deckcraft')
env=dict(os.environ,DISPLAY=':0',DECKCRAFT_NO_AUDIO='1',DECKCRAFT_STATIC_CARET='1',
         XDG_CONFIG_HOME=str(base/'config'),XDG_DATA_HOME=str(base/'data'),LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
env.pop('DECKCRAFT_NO_PREFS',None);env.pop('DECKCRAFT_NO_RECOVERY',None)
result={};process=None;connection=None;serial=0
def start():
    global process,connection,channel
    log=(base/'application.log').open('a')
    process=subprocess.Popen([binary,'--control','7994'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
    until=time.monotonic()+30
    while time.monotonic()<until:
        try:connection=socket.create_connection(('127.0.0.1',7994),timeout=30);break
        except OSError:time.sleep(.2)
    assert connection,'No control connection';channel=connection.makefile('rwb',buffering=0)
def request(method,params=None):
    global serial
    serial+=1;channel.write((json.dumps({'id':serial,'method':method,'params':params or {}})+'\n').encode())
    reply=json.loads(channel.readline().decode());assert reply.get('ok'),reply
    return reply.get('result')
def execute(command,params=None):return request('engine.execute',{'command':command,'params':params or {}})
try:
    subprocess.run(['xscreensaver-command','-deactivate'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    start();request('ui.focus');execute('file.new')
    shape=execute('insert.textBox',{'rect':[60,100,700,90],'text':'Original unsaved DeckCraft recovery marker.'})
    execute('text.edit',{'id':shape['id'],'end':True})
    execute('app.closePresentation');state=request('ui.inspect')
    assert state['dialog']=='close' and state['documents'],'Dirty close did not ask first'
    request('ui.dialog.close');state=request('ui.inspect')
    assert state['dialog'] is None and state['documents'][0]['dirty']
    result['close_cancel_preserves_unsaved_document']=True
    # No UI requests during this wait: a timer must wake a quiet steady-caret editor.
    time.sleep(13)
    folder=base/'data/deckcraft/recovery'
    result['automatic_idle_snapshot']=bool(list(folder.glob('*.deckcraft')))
    result['manual_snapshot']=execute('file.recovery.save')
    process.kill();process.wait(timeout=10);connection.close();connection=None
    start();time.sleep(.7)
    state=request('ui.inspect');result['restored_state']=state
    assert state['documents'],'Recovery did not reopen a document'
    assert 'Original unsaved DeckCraft recovery marker.' in json.dumps(execute('slide.inspect',{'index':0}))
    saved=base/'recovered.pptx';request('app.save',{'path':str(saved)})
    with zipfile.ZipFile(str(saved)) as z:
        assert b'Original unsaved DeckCraft recovery marker.' in z.read('ppt/slides/slide1.xml')
    result['restored_and_saved_marker']=True
    request('app.quit');process.wait(timeout=10)
    result['passed']=result['automatic_idle_snapshot']
except Exception as error:result.update(passed=False,error=str(error))
finally:
    if connection:connection.close()
    if process and process.poll() is None:process.terminate();process.wait(timeout=10)
result['profile']=str(base)
Path('/tmp/vaio-deckcraft-test/recovery-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(0 if result.get('passed') else 1)
