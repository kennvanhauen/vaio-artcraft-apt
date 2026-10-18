#!/usr/bin/env python3
"""Click each installed card's Open action; touch only owned disposable children."""
import ctypes,json,os,re,signal,subprocess,time
from pathlib import Path
base=Path('/tmp/vaio-vectorcraft-test/launcher-five-open');base.mkdir(parents=True,exist_ok=True)
(base/'runtime').mkdir(exist_ok=True,mode=0o700)
env=dict(os.environ,DISPLAY=':0',WORDCRAFT_PROFILE_DIR=str(base/'word-profile'),WORDCRAFT_NO_PREFS='1',GRIDCRAFT_NO_PREFS='1',DECKCRAFT_NO_PREFS='1',DECKCRAFT_NO_RECOVERY='1',DECKCRAFT_NO_AUDIO='1',VECTORCRAFT_NO_PREFS='1',PDFCRAFT_SYSTEM_FONTS='0',XDG_RUNTIME_DIR=str(base/'runtime'),XDG_DATA_HOME=str(base/'data'),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'))
x11=ctypes.CDLL('libX11.so.6');xtst=ctypes.CDLL('libXtst.so.6')
x11.XOpenDisplay.argtypes=[ctypes.c_char_p];x11.XOpenDisplay.restype=ctypes.c_void_p
x11.XSetInputFocus.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
x11.XRaiseWindow.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x11.XFlush.argtypes=[ctypes.c_void_p];x11.XCloseDisplay.argtypes=[ctypes.c_void_p]
xtst.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
xtst.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
log=(base/'application.log').open('w');p=subprocess.Popen(['/usr/bin/vaio-app-launcher'],env=env,stdout=log,stderr=log)
result={'opened':[]};children=[]
def window():
    tree=subprocess.check_output(['xwininfo','-root','-tree'],env=env).decode()
    for wid in re.findall(r'^\s+(0x[0-9a-fA-F]+)',tree,re.M):
        prop=subprocess.run(['xprop','-id',wid,'_NET_WM_PID'],env=env,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL).stdout.decode()
        if not re.search(r'=\s*%d\s*$'%p.pid,prop):continue
        info=subprocess.check_output(['xwininfo','-id',wid],env=env).decode()
        if 'Map State: IsViewable' in info:
            return int(wid,16),int(re.search(r'Absolute upper-left X:\s+(-?\d+)',info).group(1)),int(re.search(r'Absolute upper-left Y:\s+(-?\d+)',info).group(1))
    raise RuntimeError('Own launcher window unavailable')
try:
    time.sleep(7)
    for app,x in [('vectorcraft',170),('pdfcraft',470),('wordcraft',770),('deckcraft',1070),('gridcraft',1370)]:
        wid,ox,oy=window();display=x11.XOpenDisplay(b':0');assert display
        try:
            x11.XRaiseWindow(display,wid);x11.XSetInputFocus(display,wid,2,0)
            xtst.XTestFakeMotionEvent(display,-1,ox+x,oy+365,0)
            xtst.XTestFakeButtonEvent(display,1,1,0);xtst.XTestFakeButtonEvent(display,1,0,0);x11.XFlush(display)
        finally:x11.XCloseDisplay(display)
        found=None;until=time.monotonic()+8
        while time.monotonic()<until:
            ids=Path('/proc/%d/task/%d/children'%(p.pid,p.pid)).read_text().split()
            for value in ids:
                pid=int(value)
                try:
                    command=Path('/proc/%d/cmdline'%pid).read_bytes().split(b'\0')[0]
                    profile=Path('/proc/%d/environ'%pid).read_bytes().split(b'\0')
                    if command==('/usr/lib/'+app+'-vaio/bin/'+app).encode() and ('XDG_DATA_HOME='+str(base/'data')).encode() in profile:found=pid;break
                except OSError:pass
            if found:break
            time.sleep(.2)
        assert found,'Open did not launch '+app
        children.append(found);time.sleep(2)
        assert Path('/proc/%d'%found).exists(),app+' exited at startup'
        os.kill(found,signal.SIGTERM)
        until=time.monotonic()+4
        while time.monotonic()<until and Path('/proc/%d'%found).exists():time.sleep(.1)
        assert not Path('/proc/%d'%found).exists(),'Child was not reaped: '+app
        result['opened'].append(app)
    result['passed']=True
except Exception as error:result.update(passed=False,error=str(error))
finally:
    for child in children:
        try:
            status=Path('/proc/%d/status'%child).read_text()
            if re.search(r'^PPid:\s+%d$'%p.pid,status,re.M):os.kill(child,signal.SIGTERM)
        except OSError:pass
    p.terminate();p.wait(timeout=10);log.close()
(base/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(0 if result.get('passed') else 1)
