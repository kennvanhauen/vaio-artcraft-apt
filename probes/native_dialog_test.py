#!/usr/bin/env python3
"""Exercise native GTK Open/Save dialogs using synthetic files and owned windows."""
import ctypes,json,os,re,subprocess,time,sys
from pathlib import Path
from vaio_test_support import App
base=Path('/tmp/vaio-everyday')
app=App(base/'dialogs',7986,binary=os.environ.get('VAIO_TEST_BINARY','/usr/bin/wordcraft-vaio'),file=base/'report.docx')
result={};pickers=[]
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
    app.request('ui.resize',{'width':1100,'height':650})
    time.sleep(1)
    app.execute('file.open')
    pid,window=picker()
    result['open_dialog_observed']=True
    # The app must continue servicing requests while a native chooser is open.
    result['responsive_during_open']=bool(app.request('ui.inspect'))
    chord('Control_L','l');type_path(base/'edited.docx');tap('Return');x11.XFlush(display)
    until=time.monotonic()+10
    while time.monotonic()<until:
        state=app.request('ui.inspect')
        if state['title']=='edited':break
        time.sleep(.3)
    assert state['title']=='edited',state['title']
    result['open_selected_file']=True
    app.execute('file.saveAs')
    pid,window=picker();result['save_dialog_observed']=True
    target=base/('native-bare.docx' if '--bare' in sys.argv else 'native-saved.docx')
    typed=target.with_suffix('') if '--bare' in sys.argv else target
    if target.exists():target.unlink() # disposable test output only
    chord('Alt_L','n');chord('Control_L','a');type_path(typed);tap('Return');x11.XFlush(display)
    until=time.monotonic()+10
    while time.monotonic()<until and not target.exists():time.sleep(.25)
    assert target.exists(),'Native save did not produce output'
    content=subprocess.check_output([os.environ.get('VAIO_WORDCRAFT_CLI','/usr/bin/wordcraft-vaio-cli'),'text',str(target)]).decode()
    assert os.environ.get('VAIO_TEST_EXPECTED_TEXT','Final edited sentence.') in content
    result['save_selected_file']=True
    if '--bare' in sys.argv:
        marker=b'Existing synthetic file: must remain unchanged when replacement is cancelled.'
        protected=base/'protected.docx'
        protected.write_bytes(marker)
        app.execute('file.saveAs');pid,window=picker()
        chord('Alt_L','n');chord('Control_L','a');type_path(protected.with_suffix(''));tap('Return');x11.XFlush(display)
        pid,window=picker(question=True)
        result['normalized_overwrite_confirmation_observed']=True
        tap('Escape');x11.XFlush(display);time.sleep(.3)
        assert protected.read_bytes()==marker,'Normalized save overwrote without agreement'
        result['cancelled_overwrite_preserves_existing_file']=True
    result['passed']=True
except Exception as error:result.update(passed=False,error=str(error))
finally:
    for pid in pickers:
        try:
            status=Path('/proc/%d/status'%pid).read_text()
            if re.search(r'^PPid:\s+%d$'%app.process.pid,status,re.M):os.kill(pid,15)
        except OSError:pass
    x11.XCloseDisplay(display);app.close()
result['timings']=app.timings
(base/('native-bare-result.json' if '--bare' in sys.argv else 'native-dialog-result.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result.get('passed') else 1)
