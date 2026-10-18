#!/usr/bin/env python3
import ctypes,json,os,re,socket,subprocess,time,zipfile
from pathlib import Path
from types import SimpleNamespace
os.environ['DISPLAY']=':0'
base=Path('/tmp/vaio-figcraft-test/native-dialogs');base.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,DISPLAY=':0',FIGCRAFT_NO_SYSTEM_FONTS='1',XDG_CONFIG_HOME=str(base/'config'),XDG_DATA_HOME=str(base/'data'),XDG_CACHE_HOME=str(base/'cache'),LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
log=(base/'application.log').open('w')
p=subprocess.Popen([os.environ.get('VAIO_FIG_BINARY','/tmp/vaio-figcraft-test/figcraft'),'--control','7995','/tmp/vaio-figcraft-test/repair-club.figcraft'],env=env,stdout=log,stderr=log)
app=SimpleNamespace(process=p);result={};pickers=[];connection=None
until=time.monotonic()+25
while time.monotonic()<until:
    try:connection=socket.create_connection(('127.0.0.1',7995),timeout=30);break
    except OSError:time.sleep(.2)
assert connection,'Fig control unavailable'
channel=connection.makefile('rwb',buffering=0);serial=0
def send(method,params=None):
    global serial
    serial+=1;channel.write((json.dumps({'id':serial,'method':method,'params':params or {}})+'\n').encode())
def receive(allow_pending=False):
    response=json.loads(channel.readline().decode())
    # The async native chooser suspends/replays the UI command; its first control reply is cancelled.
    if allow_pending and response.get('error')=='cancelled':return None
    assert response.get('ok'),response
    return response.get('result')
x11=ctypes.CDLL('libX11.so.6');xtst=ctypes.CDLL('libXtst.so.6')
x11.XOpenDisplay.argtypes=[ctypes.c_char_p];x11.XOpenDisplay.restype=ctypes.c_void_p
x11.XStringToKeysym.argtypes=[ctypes.c_char_p];x11.XStringToKeysym.restype=ctypes.c_ulong
x11.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x11.XKeysymToKeycode.restype=ctypes.c_ubyte
x11.XSetInputFocus.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
x11.XRaiseWindow.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
x11.XFlush.argtypes=[ctypes.c_void_p];x11.XCloseDisplay.argtypes=[ctypes.c_void_p]
xtst.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
display=x11.XOpenDisplay(b':0')
if not display:raise RuntimeError('No X display')
def key(name,pressed):
    code=x11.XKeysymToKeycode(display,x11.XStringToKeysym(name.encode()))
    if not code:raise RuntimeError('No test key: '+name)
    xtst.XTestFakeKeyEvent(display,code,int(pressed),0)
def tap(name):key(name,True);key(name,False)
def chord(mod,name):key(mod,True);tap(name);key(mod,False);x11.XFlush(display);time.sleep(.15)
def type_path(path):
    names={'/':'slash','-':'minus','.':'period',' ':'space'}
    for c in str(path):tap(names.get(c,c))
    x11.XFlush(display);time.sleep(.2)
def picker(question=False):
    until=time.monotonic()+12
    while time.monotonic()<until:
        rows=subprocess.check_output(['ps','-eo','pid,ppid,comm']).decode().splitlines()
        pids=[int(p[0]) for line in rows for p in [line.split()] if len(p)==3 and p[1]==str(app.process.pid) and p[2]=='zenity']
        if pids:
            pid=pids[0]
            if question and b'--question' not in Path('/proc/%d/cmdline'%pid).read_bytes():
                time.sleep(.2);continue
            pickers.append(pid)
            tree=subprocess.check_output(['xwininfo','-root','-tree'],env=dict(os.environ,DISPLAY=':0')).decode()
            for wid in re.findall(r'^\s+(0x[0-9a-fA-F]+)',tree,re.M):
                prop=subprocess.run(['xprop','-id',wid,'_NET_WM_PID'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL).stdout.decode()
                if re.search(r'=\s*%d\s*$'%pid,prop):
                    details=subprocess.check_output(["xwininfo","-id",wid]).decode()
                    if "Map State: IsViewable" not in details:continue
                    window=int(wid,16);x11.XRaiseWindow(display,window);x11.XSetInputFocus(display,window,2,0);x11.XFlush(display)
                    time.sleep(.2);return pid,window
        time.sleep(.25)
    raise RuntimeError('Native file chooser not observed')
def request(method,params=None):
    send(method,params);return receive()
def dialog(kind):
    until=time.monotonic()+12
    while time.monotonic()<until:
        state=request('ui.inspect');d=state.get('dialog')
        if d and d.get('kind')==kind:return d
        time.sleep(.2)
    raise RuntimeError('Expected '+kind+' dialog; last '+str(d))
try:
    until=time.monotonic()+15
    while time.monotonic()<until:
        state=request('ui.inspect')
        if state['tabs']:break
        time.sleep(.2)
    assert state['tabs'],'Document did not finish opening'
    send('ui.menu.invoke',{'id':'file.saveAs'});picker()
    target=base/'native-bare.figcraft'
    for output in [target,target.with_suffix('')]:
        if output.exists():output.unlink()
    chord('Alt_L','n');chord('Control_L','a');type_path(target.with_suffix(''));tap('Return');x11.XFlush(display)
    receive()
    until=time.monotonic()+12
    while time.monotonic()<until and not target.exists():time.sleep(.2)
    assert target.exists(),'Bare-name native save failed'
    cli=os.environ.get('VAIO_FIG_CLI','/tmp/vaio-figcraft-test/figcraft-cli')
    subprocess.run([cli,'convert',str(target),str(base/'saved.pdf')],env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    text=subprocess.check_output(['pdftotext',str(base/'saved.pdf'),'-']).decode()
    assert 'THE REPAIR CLUB' in text
    result['native_bare_name_save']=True
    marker=b'Existing synthetic target to preserve';protected=base/'protected.figcraft';protected.write_bytes(marker)
    send('ui.menu.invoke',{'id':'file.saveAs'});picker()
    chord('Alt_L','n');chord('Control_L','a');type_path(protected.with_suffix(''));tap('Return');x11.XFlush(display)
    receive();time.sleep(.8)
    assert protected.read_bytes()==marker
    state=request('document.inspect')
    assert state['path']==str(target),state
    result['normalized_overwrite_refusal_preserves_target']=True
    request('app.quit');p.wait(timeout=10);result['passed']=True
except Exception as error:result.update(passed=False,error=str(error))
finally:
    for pid in pickers:
        try:
            status=Path('/proc/%d/status'%pid).read_text()
            if re.search(r'^PPid:\s+%d$'%p.pid,status,re.M):os.kill(pid,15)
        except OSError:pass
    x11.XCloseDisplay(display)
    if p.poll() is None:p.terminate();p.wait(timeout=10)
    connection.close();log.close()
(base/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(0 if result.get('passed') else 1)
