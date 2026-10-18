#!/usr/bin/env python3
"""Open the installed six-app launcher, measure settled use and leave it visible."""
import ctypes,json,os,re,subprocess,time
from pathlib import Path
os.environ['DISPLAY']=':0'
env=dict(os.environ,DISPLAY=':0')
log=open('/tmp/vaio-designcraft-test/final-launcher.log','a')
p=subprocess.Popen(['/usr/bin/vaio-app-launcher'],env=env,stdin=subprocess.DEVNULL,
                   stdout=log,stderr=log,start_new_session=True)
time.sleep(3)
# Fit all six cards in the owned launcher, preserving the rest of its settings.
x11=ctypes.CDLL('libX11.so.6')
x11.XOpenDisplay.argtypes=[ctypes.c_char_p];x11.XOpenDisplay.restype=ctypes.c_void_p
x11.XMoveResizeWindow.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_int,ctypes.c_uint,ctypes.c_uint]
x11.XRaiseWindow.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
x11.XFlush.argtypes=[ctypes.c_void_p];x11.XCloseDisplay.argtypes=[ctypes.c_void_p]
subprocess.run(['xscreensaver-command','-deactivate'],env=env,stdout=subprocess.DEVNULL)
tree=subprocess.check_output(['xwininfo','-root','-tree'],env=env).decode()
for wid in re.findall(r'^\s+(0x[0-9a-fA-F]+)',tree,re.M):
    prop=subprocess.run(['xprop','-id',wid,'_NET_WM_PID'],env=env,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL).stdout.decode()
    if not re.search(r'=\s*%d\s*$'%p.pid,prop):continue
    info=subprocess.check_output(['xwininfo','-id',wid],env=env).decode()
    if 'Map State: IsViewable' not in info:continue
    display=x11.XOpenDisplay(b':0');assert display
    x11.XMoveResizeWindow(display,int(wid,16),20,35,1540,650);x11.XRaiseWindow(display,int(wid,16));x11.XFlush(display);x11.XCloseDisplay(display)
    break
else:raise RuntimeError('Owned final launcher window unavailable')
def sample():
    f=Path('/proc/%d/stat'%p.pid).read_text().rsplit(')',1)[1].split()
    rss=next(int(line.split()[1]) for line in Path('/proc/%d/status'%p.pid).read_text().splitlines() if line.startswith('VmRSS:'))
    return int(f[11])+int(f[12]),rss
time.sleep(55)
before,rss=sample();at=time.monotonic();time.sleep(7);after,rss=sample();duration=time.monotonic()-at
state=json.loads(subprocess.check_output(['/usr/bin/vaio-app-launcher','--check'],env=env).decode())
result={'pid':p.pid,'left_visible':True,'rss_kib':rss,
        'idle_cpu_percent_one_logical_cpu':round(100*(after-before)/os.sysconf('SC_CLK_TCK')/duration,2),
        'installed_apps':[{k:app[k] for k in ['package','installed','candidate']} for app in state['applications']]}
result['passed']=len(state['applications'])==6 and all(app['installed'] and app['installed']==app['candidate'] for app in state['applications'])
Path('/tmp/vaio-designcraft-test/final-launcher-result.json').write_text(json.dumps(result,indent=2)+'\n')
# Capture only the owned launcher rectangle after its package check settles.
import gi
gi.require_version('Gdk','3.0')
from gi.repository import Gdk
info=subprocess.check_output(['xwininfo','-id',wid],env=env).decode()
x=int(re.search(r'Absolute upper-left X:\s+(-?\d+)',info).group(1))
y=int(re.search(r'Absolute upper-left Y:\s+(-?\d+)',info).group(1))
w=int(re.search(r'Width:\s+(\d+)',info).group(1));h=int(re.search(r'Height:\s+(\d+)',info).group(1))
result['window']={'x':x,'y':y,'width':w,'height':h}
result['fits_screen']=x>=0 and y>=0 and x+w<=1600 and y+h<=768
image=Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),x,y,w,h)
assert image,'Window capture unavailable'
image.savev('/tmp/vaio-designcraft-test/final-launcher.png','png',[],[])
result['passed']=result['passed'] and result['fits_screen']
Path('/tmp/vaio-designcraft-test/final-launcher-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
