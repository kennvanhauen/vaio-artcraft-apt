#!/usr/bin/env python3
import ctypes,json,os,re,subprocess,time
from pathlib import Path
from types import SimpleNamespace
os.environ['DISPLAY']=':0'
base=Path('/tmp/vaio-everyday/pdfcraft-dialogs');base.mkdir(parents=True,exist_ok=True,mode=0o700)
control=base/'control.json'
if control.exists():control.unlink()
env=dict(os.environ,DISPLAY=':0',PDFCRAFT_RENDERER='gl',PDFCRAFT_SYSTEM_FONTS='0',XDG_CONFIG_HOME=str(base/'config'),XDG_DATA_HOME=str(base/'data'),XDG_CACHE_HOME=str(base/'cache'),XDG_RUNTIME_DIR=str(base),LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
log=(base/'application.log').open('w');cli='/tmp/vaio-everyday/pdfcraft-cli'
p=subprocess.Popen(['/tmp/vaio-everyday/pdfcraft','--control',str(control),'/tmp/vaio-everyday/allowed-pdf-test.pdf'],env=env,stdout=log,stderr=log)
app=SimpleNamespace(process=p);result={};pickers=[]
until=time.monotonic()+25
while time.monotonic()<until and not control.exists():time.sleep(.2)
assert control.exists(),'PDF control unavailable'
def ui(method,*args):
    return json.loads(subprocess.check_output([cli,'ui','--control',str(control),method]+list(args),env=env,timeout=30).decode())
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
try:
    time.sleep(1);ui('command','id=file.save_as');picker()
    result['responsive_during_native_dialog']=bool(ui('state'))
    target=base/'native-bare.pdf'
    for output in [target,target.with_suffix('')]:
        if output.exists():output.unlink()
    chord('Alt_L','n');chord('Control_L','a');type_path(target.with_suffix(''));tap('Return');x11.XFlush(display)
    until=time.monotonic()+10
    while time.monotonic()<until and not target.exists():time.sleep(.2)
    result['bare_file_created']=target.with_suffix('').exists()
    assert target.exists(),'Bare-name Save As did not add .pdf'
    assert target.read_bytes().startswith(b'%PDF-')
    result['native_bare_name_save']=True
    marker=b'Existing synthetic target to preserve';protected=base/'protected.pdf';protected.write_bytes(marker)
    ui('command','id=file.save_as');picker()
    chord('Alt_L','n');chord('Control_L','a');type_path(protected.with_suffix(''));tap('Return');x11.XFlush(display)
    picker(question=True);tap('Escape');x11.XFlush(display);time.sleep(.3)
    assert protected.read_bytes()==marker
    result['normalized_overwrite_cancel_preserves_target']=True
    ui('quit');p.wait(timeout=10);result['passed']=True
except Exception as e:result.update(passed=False,error=str(e))
finally:
    for pid in pickers:
        try:
            status=Path('/proc/%d/status'%pid).read_text()
            if re.search(r'^PPid:\s+%d$'%p.pid,status,re.M):os.kill(pid,15)
        except OSError:pass
    x11.XCloseDisplay(display)
    if p.poll() is None:p.terminate();p.wait(timeout=10)
    log.close()
(base/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(0 if result.get('passed') else 1)
