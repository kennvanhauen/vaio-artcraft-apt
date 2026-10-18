#!/usr/bin/env python3
"""Bounded real-VAIO illustration editing, path operations, save/export and idle check."""
import json, os, socket, subprocess, time
from pathlib import Path
base = Path('/tmp/vaio-vectorcraft-test')
binary = os.environ.get('VAIO_VECTOR_BINARY',str(base/'vectorcraft'))
env = dict(os.environ,DISPLAY=':0',VECTORCRAFT_NO_PREFS='1',XDG_CONFIG_HOME=str(base/'gui-config'),XDG_DATA_HOME=str(base/'gui-data'),XDG_CACHE_HOME=str(base/'gui-cache'),LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
result = {'checks': [], 'timings': []}
process = None
connection = None
try:
    subprocess.run(['xscreensaver-command','-deactivate'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    log = (base/'gui.log').open('w')
    process = subprocess.Popen([binary,'--control','7993','--automation-read-root',str(base),'--automation-write-root',str(base),str(base/'original.vectorcraft')],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
    until = time.monotonic()+40
    while time.monotonic()<until:
        if process.poll() is not None:raise RuntimeError('GUI exited during startup')
        try:connection=socket.create_connection(('127.0.0.1',7993),timeout=60);break
        except OSError:time.sleep(.2)
    assert connection, 'Control endpoint unavailable'
    channel = connection.makefile('rwb',buffering=0)
    serial = 0
    def request(method,params=None):
        global serial
        serial += 1
        at = time.monotonic()
        channel.write((json.dumps({'id':serial,'method':method,'params':params or {}})+'\n').encode())
        reply = json.loads(channel.readline().decode())
        result['timings'].append({'action':method,'seconds':round(time.monotonic()-at,3)})
        if not reply.get('ok'):raise RuntimeError(method+': '+str(reply.get('error')))
        return reply.get('result')
    def execute(command,params=None):return request('engine.execute',{'command':command,'params':params or {}})
    time.sleep(2)
    result['initial_ui'] = request('ui.inspect')
    request('ui.resize',{'width':1100,'height':650})
    created = execute('text.create',{'x':34,'y':155,'text':'Edit here','font':'Inter','size':16})
    result['created_text'] = created
    request('ui.tool.select',{'tool':'type'})
    bounds = created['bounds']
    x,y = bounds['x']+bounds['width']/2,bounds['y']+bounds['height']/2
    request('ui.pointer',{'events':[{'kind':'down','x':x,'y':y,'space':'doc'},{'kind':'up','x':x,'y':y,'space':'doc'}]})
    editing = request('ui.inspect')
    assert editing['toolOptions'].get('editing') == created['id'], editing['toolOptions']
    execute('select.all')
    request('ui.text',{'text':'Edited on the Sony VAIO'})
    until = time.monotonic()+8
    while time.monotonic()<until:
        result['edited_text'] = request('document.inspect',{'kind':'Type'})
        if 'Edited on the Sony VAIO' in json.dumps(result['edited_text']):break
        time.sleep(.1)
    assert 'Edited on the Sony VAIO' in json.dumps(result['edited_text'])
    request('ui.screenshot',{'path':str(base/'editing-ui.png')})
    def sample():
        stat = Path('/proc/%d/stat'%process.pid).read_text().rsplit(')',1)[1].split()
        rss = next(int(l.split()[1]) for l in Path('/proc/%d/status'%process.pid).read_text().splitlines() if l.startswith('VmRSS:'))
        return int(stat[11])+int(stat[12]), rss
    def idle():
        time.sleep(2);before,rss=sample();at=time.monotonic();time.sleep(5);after,rss=sample()
        return {'cpu_percent_one_logical_cpu':round(100*(after-before)/os.sysconf('SC_CLK_TCK')/(time.monotonic()-at),2),'rss_kib':rss}
    result['editing_idle'] = idle()
    request('ui.key',{'key':'Escape'})
    execute('layer.new',{'name':'Original badge'})
    execute('paint.setFill',{'color':'#e3a13c'})
    a=execute('shape.rectangle',{'x':250,'y':145,'width':60,'height':45,'radius':5})['id']
    b=execute('shape.ellipse',{'x':285,'y':140,'width':50,'height':50})['id']
    execute('select.set',{'ids':[a,b]})
    result['united'] = execute('object.pathfinder.unite')
    execute('edit.undo');execute('edit.redo')
    execute('artboard.new',{'x':520,'y':0,'width':240,'height':160,'name':'Badge detail'})
    execute('text.create',{'x':540,'y':40,'text':'MAKE AND MEND','font':'Inter','size':15})
    execute('shape.star',{'cx':640,'cy':100,'radius1':32,'radius2':15,'points':5})
    execute('select.none')
    request('app.save',{'path':str(base/'gui-edited.vectorcraft')})
    request('app.export',{'path':str(base/'gui-edited.pdf')})
    request('app.export',{'path':str(base/'gui-edited.svg')})
    request('ui.render',{'path':str(base/'gui-edited.png'),'scale':1})
    until=time.monotonic()+20
    while time.monotonic()<until:
        state=request('ui.inspect')
        if not state.get('background'):break
        time.sleep(.2)
    assert not state.get('background'),state['background']
    request('app.open',{'path':str(base/'gui-edited.vectorcraft')})
    until=time.monotonic()+15
    while time.monotonic()<until:
        state=request('ui.inspect')
        if not state.get('opening'):break
        time.sleep(.2)
    result['reopened'] = request('document.inspect',{'depth':3})
    assert len(result['reopened']['artboards']) == 2
    assert 'Edited on the Sony VAIO' in json.dumps(result['reopened'])
    request('ui.screenshot',{'path':str(base/'vectorcraft-ui.png')})
    result['settled_idle'] = idle()
    result['private_xcb'] = sorted(set(l.split()[-1] for l in Path('/proc/%d/maps'%process.pid).read_text().splitlines() if '/lib/libxcb.so.1' in l))
    request('app.quit');process.wait(timeout=15)
    result['checks'] += ['OpenGL startup','GUI text input','layers','rectangle/ellipse/star','pathfinder union','undo/redo','two artboards','native save/reopen','PDF/SVG/PNG export']
    result['passed'] = True
except Exception as error:result.update(passed=False,error=str(error))
finally:
    if process and process.poll() is None:process.terminate();process.wait(timeout=10)
    if connection:connection.close()
(base/'gui-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('initial_ui','reopened','edited_text')},indent=2))
raise SystemExit(0 if result.get('passed') else 1)
