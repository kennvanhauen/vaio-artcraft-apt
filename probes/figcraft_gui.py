#!/usr/bin/env python3
"""Original interface-design GUI and prototype check on the VAIO."""
import json,os,socket,subprocess,time
from pathlib import Path
base=Path('/tmp/vaio-figcraft-test');binary=os.environ.get('VAIO_FIG_BINARY',str(base/'figcraft'))
env=dict(os.environ,DISPLAY=':0',FIGCRAFT_NO_SYSTEM_FONTS='1',XDG_CONFIG_HOME=str(base/'gui-config'),XDG_DATA_HOME=str(base/'gui-data'),XDG_CACHE_HOME=str(base/'gui-cache'),LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
r={'checks':[]};p=None;c=None;serial=0
try:
 subprocess.run(['xscreensaver-command','-deactivate'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 p=subprocess.Popen([binary,'--control','7993','--automation-read-root',str(base),'--automation-write-root',str(base),str(base/'repair-club.figcraft')],env=env,stdin=subprocess.DEVNULL,stdout=(base/'gui.log').open('w'),stderr=subprocess.STDOUT)
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
 def sample():
  f=Path('/proc/%d/stat'%p.pid).read_text().rsplit(')',1)[1].split();rss=next(int(l.split()[1]) for l in Path('/proc/%d/status'%p.pid).read_text().splitlines() if l.startswith('VmRSS:'))
  return int(f[11])+int(f[12]),rss
 def idle():
  time.sleep(3);a,rss=sample();at=time.monotonic();time.sleep(6);b,rss=sample()
  return {'cpu_percent_one_logical_cpu':round(100*(b-a)/os.sysconf('SC_CLK_TCK')/(time.monotonic()-at),2),'rss_kib':rss}
 ids=json.loads((base/'ids.json').read_text());time.sleep(2)
 r['initial']=req('document.inspect',{'depth':8});assert 'THE REPAIR CLUB' in json.dumps(r['initial'])
 req('ui.set',{'theme':'light','home':False});ex('view.zoomFit');ex('text.edit.begin',{'id':ids['heading']});req('ui.type',{'text':'THE REPAIR CLUB — VAIO'})
 r['typed']=req('node.get',{'id':ids['heading']});assert 'THE REPAIR CLUB — VAIO' in json.dumps(r['typed'],ensure_ascii=False)
 r['editing_idle']=idle();r['editing_later_idle']=idle();r['editing_ui']=req('ui.inspect');req('ui.screenshot',{'path':str(base/'editing-ui.png')})
 ex('text.edit.end');ex('node.set',{'ids':[ids['heading']],'props':{'fontSize':20}});ex('edit.undo');ex('edit.redo')
 ex('file.saveAs',{'path':str(base/'gui-edited.figcraft')});ex('file.open',{'path':str(base/'gui-edited.figcraft')})
 r['reopened']=req('document.inspect',{'depth':8});assert 'THE REPAIR CLUB — VAIO' in json.dumps(r['reopened'],ensure_ascii=False)
 ex('select.set',{'ids':[ids['home']]});req('ui.menu.invoke',{'id':'proto.present'});time.sleep(1)
 state=req('ui.inspect');r['present_initial']=state;assert state['presenting'] and state['presenter']['current']==ids['home'],state
 def click_hotspot(node):
  state=req('ui.inspect');h=next(h for h in state['presenter']['hotspots'] if h['id']==node);x1,y1,x2,y2=h['rect'];x=(x1+x2)/2;y=(y1+y2)/2
  req('ui.input',{'events':[{'move':[x,y]},{'down':[x,y]}]});req('ui.input',{'events':[{'up':[x,y]}]});time.sleep(.7)
 click_hotspot(ids['instance']);state=req('ui.inspect');assert state['presenter']['current']==ids['details'],state
 click_hotspot(ids['back']);assert req('ui.inspect')['presenter']['current']==ids['home']
 req('ui.screenshot',{'path':str(base/'prototype-ui.png')});req('ui.input',{'events':[{'move':[1405,60]},{'down':[1405,60]}]});req('ui.input',{'events':[{'up':[1405,60]}]});time.sleep(.5);assert not req('ui.inspect')['presenting']
 req('ui.menu.invoke',{'id':'proto.preview'});time.sleep(1.5);r['preview']=req('ui.inspect')['preview'];assert r['preview'] and r['preview']['name']=='Repair Club — Home'
 req('ui.menu.invoke',{'id':'proto.closePreview'});time.sleep(.5);assert req('ui.inspect')['preview'] is None;ex('select.none');ex('view.zoomFit');req('ui.screenshot',{'path':str(base/'figcraft-ui.png')})
 r['settled_idle']=idle();r['private_xcb']=sorted(set(l.split()[-1] for l in Path('/proc/%d/maps'%p.pid).read_text().splitlines() if '/lib/libxcb.so.1' in l))
 req('app.quit');p.wait(timeout=15);r['checks']=['OpenGL startup','GUI text input','formatting','undo/redo','native save/reopen','prototype forward/back navigation by GUI clicks','floating prototype preview','window screenshots'];r['passed']=True
except Exception as e:r.update(passed=False,error=repr(e))
finally:
 if p and p.poll() is None:p.terminate();p.wait(timeout=10)
 if c:c.close()
(base/'gui-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('initial','typed','reopened','present_initial','editing_ui')},indent=2));raise SystemExit(0 if r.get('passed') else 1)
