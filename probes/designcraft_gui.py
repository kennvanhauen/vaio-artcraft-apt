#!/usr/bin/env python3
"""Modest native GUI editing/save/reopen and measured idle use on the VAIO."""
import json,os,socket,subprocess,time
from pathlib import Path
base=Path('/tmp/vaio-designcraft-test');binary=os.environ.get('VAIO_DESIGN_BINARY',str(base/'designcraft'))
env=dict(os.environ,DISPLAY=':0',DESIGNCRAFT_NO_PREFS='1',DESIGNCRAFT_CONFIG_DIR=str(base/'gui-profile'),LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
result={'checks':[]};p=None;connection=None;serial=0
try:
    subprocess.run(['xscreensaver-command','-deactivate'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    p=subprocess.Popen([binary,'--control','7993',str(base/'original.designcraft')],env=env,stdin=subprocess.DEVNULL,stdout=(base/'gui.log').open('w'),stderr=subprocess.STDOUT)
    until=time.monotonic()+45
    while time.monotonic()<until:
        if p.poll() is not None:raise RuntimeError('GUI exited at startup')
        try:connection=socket.create_connection(('127.0.0.1',7993),timeout=60);break
        except OSError:time.sleep(.2)
    assert connection
    channel=connection.makefile('rwb',buffering=0)
    def request(method,params=None):
        global serial
        serial+=1;channel.write((json.dumps({'id':serial,'method':method,'params':params or {}})+'\n').encode());r=json.loads(channel.readline().decode())
        if not r.get('ok'):raise RuntimeError(method+': '+str(r))
        return r.get('result')
    def execute(c,p=None):return request('engine.execute',{'command':c,'params':p or {}})
    time.sleep(2);result['initial']=request('document.inspect');assert result['initial']['pageCount']==3
    request('ui.resize',{'width':1300,'height':650})
    request('ui.set',{'fit':'page','page':1})
    heading=next(s for s in result['initial']['stories'] if 'THE REPAIR CLUB' in s['preview'])
    request('ui.tool.select',{'tool':'type'})
    execute('text.select',{'story':heading['id'],'anchor':0,'focus':heading['length']})
    request('ui.text',{'text':'THE REPAIR CLUB — VAIO'})
    time.sleep(.8)
    result['typed']=request('document.inspect');assert any(s['preview']=='THE REPAIR CLUB — VAIO' for s in result['typed']['stories']), result['typed']['stories']
    execute('type.char',{'attrs':{'size':23}})
    request('ui.screenshot',{'path':str(base/'editing-ui.png')})
    def sample():
        f=Path('/proc/%d/stat'%p.pid).read_text().rsplit(')',1)[1].split()
        rss=next(int(l.split()[1]) for l in Path('/proc/%d/status'%p.pid).read_text().splitlines() if l.startswith('VmRSS:'))
        return int(f[11])+int(f[12]),rss
    def idle():
        time.sleep(3);a,rss=sample();at=time.monotonic();time.sleep(6);b,rss=sample()
        return {'cpu_percent_one_logical_cpu':round(100*(b-a)/os.sysconf('SC_CLK_TCK')/(time.monotonic()-at),2),'rss_kib':rss}
    result['editing_idle']=idle()
    request('ui.key',{'key':'Escape'})
    request('ui.tool.select',{'tool':'selection'})
    execute('edit.undo');execute('edit.redo')
    request('app.save',{'path':str(base/'gui-edited.designcraft')})
    execute('file.exportPdf',{'path':str(base/'gui-edited.pdf')})
    request('ui.render',{'path':str(base/'gui-edited.png'),'page':1,'scale':1})
    request('app.open',{'path':str(base/'gui-edited.designcraft')})
    result['reopened']=request('document.inspect');assert result['reopened']['pageCount']==3 and 'THE REPAIR CLUB — VAIO' in json.dumps(result['reopened'],ensure_ascii=False)
    request('ui.set',{'fit':'page','page':1})
    request('ui.screenshot',{'path':str(base/'designcraft-ui.png')})
    result['settled_idle']=idle()
    result['private_xcb']=sorted(set(l.split()[-1] for l in Path('/proc/%d/maps'%p.pid).read_text().splitlines() if '/lib/libxcb.so.1' in l))
    request('app.quit');p.wait(timeout=15)
    result['checks']=['OpenGL startup','GUI text input','character formatting','undo/redo','native save/reopen','PDF/PNG export','window screenshot']
    result['passed']=True
except Exception as e:result.update(passed=False,error=repr(e))
finally:
    if p and p.poll() is None:p.terminate();p.wait(timeout=10)
    if connection:connection.close()
(base/'gui-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('initial','typed','reopened')},indent=2))
raise SystemExit(0 if result.get('passed') else 1)
