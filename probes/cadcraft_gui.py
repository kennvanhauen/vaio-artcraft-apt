#!/usr/bin/env python3
"""Actual CPU/Glow drawing, interactive command input and short idle samples."""
import json,os,socket,subprocess,time
from pathlib import Path
base=Path('/tmp/vaio-cadcraft-test');binary=os.environ.get('VAIO_CAD_BINARY',str(base/'cadcraft'))
env=dict(os.environ,DISPLAY=':0',CADCRAFT_CONFIG_DIR=str(base/'gui-profile'),XDG_CONFIG_HOME=str(base/'gui-config'),XDG_DATA_HOME=str(base/'gui-data'),XDG_CACHE_HOME=str(base/'gui-cache'),LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
r={};p=None;c=None;serial=0
try:
 subprocess.run(['xscreensaver-command','-deactivate'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 p=subprocess.Popen([binary,'--control','7993',str(base/'repair-plate.dxf')],env=env,stdin=subprocess.DEVNULL,stdout=(base/'gui.log').open('w'),stderr=subprocess.STDOUT)
 until=time.monotonic()+45
 while time.monotonic()<until:
  if p.poll() is not None:raise RuntimeError('GUI exited at startup')
  try:c=socket.create_connection(('127.0.0.1',7993),timeout=60);break
  except OSError:time.sleep(.2)
 assert c;channel=c.makefile('rwb',buffering=0)
 def req(m,a=None):
  global serial
  serial+=1;channel.write((json.dumps({'id':serial,'method':m,'params':a or {}})+'\n').encode());q=json.loads(channel.readline().decode());assert q.get('ok'),q
  return q.get('result')
 def ex(n,a=None):return req('engine.execute',{'command':n,'params':a or {}})
 def idle():
  def sample():
   f=Path('/proc/%d/stat'%p.pid).read_text().rsplit(')',1)[1].split();rss=next(int(l.split()[1]) for l in Path('/proc/%d/status'%p.pid).read_text().splitlines() if l.startswith('VmRSS:'));return int(f[11])+int(f[12]),rss
  time.sleep(3);a,rss=sample();at=time.monotonic();time.sleep(6);b,rss=sample();return {'cpu_percent_one_logical_cpu':round(100*(b-a)/os.sysconf('SC_CLK_TCK')/(time.monotonic()-at),2),'rss_kib':rss}
 time.sleep(2);r['initial']=req('drawing.inspect',{'entities':True,'limit':100});assert 'REPAIR CLUB' in json.dumps(r['initial'],ensure_ascii=False)
 req('ui.resize',{'width':1440,'height':650});ex('zoom',{'mode':'extents'})
 r['default_idle']=idle();r['initial_ui']=req('ui.inspect');assert r['initial_ui']['perf']['renderer']=='cpu';assert r['initial_ui']['perf']['prims']>10,r['initial_ui']['perf']
 req('cmdline.input',{'text':'circle'});req('ui.pointer',{'x':60,'y':40});req('cmdline.input',{'text':'8'})
 req('cmdline.input',{'text':'text 0,115 4 0'});req('cmdline.input',{'text':'GUI EDIT ON VAIO'});req('cmdline.input',{'text':''})
 r['typed']=req('drawing.inspect',{'entities':True,'limit':100});assert 'GUI EDIT ON VAIO' in json.dumps(r['typed'])
 r['commandline_idle']=idle();ex('undo');ex('redo');req('app.save',{'path':str(base/'gui-edited.dxf')})
 ex('exportpdf',{'path':str(base/'gui-edited.pdf'),'layout':'Model','paper':'A4','fit':True,'landscape':True})
 req('app.open',{'path':str(base/'gui-edited.dxf')});ex('zoom',{'mode':'extents'});r['reopened']=req('drawing.inspect',{'entities':True,'limit':100});assert 'GUI EDIT ON VAIO' in json.dumps(r['reopened'])
 req('ui.screenshot',{'path':str(base/'cadcraft-ui.png')});r['settled_idle']=idle();r['final_ui']=req('ui.inspect')
 r['private_xcb']=sorted(set(l.split()[-1] for l in Path('/proc/%d/maps'%p.pid).read_text().splitlines() if '/lib/libxcb.so.1' in l))
 req('app.quit');p.wait(timeout=15);r['checks']=['native Glow/CPU renderer','interactive circle via world-coordinate click','command-line text input','undo/redo','native DXF save/reopen','PDF plot','window screenshot','idle measurements'];r['passed']=True
except Exception as e:r.update(passed=False,error=repr(e))
finally:
 if p and p.poll() is None:p.terminate();p.wait(timeout=10)
 if c:c.close()
(base/'gui-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['initial','typed','reopened','initial_ui','final_ui']},indent=2));raise SystemExit(0 if r.get('passed') else 1)
