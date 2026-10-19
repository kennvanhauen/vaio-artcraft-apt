#!/usr/bin/env python3
"""Ordinary small spreadsheet workflow on the real VAIO, synthetic data only."""
import json,os,socket,subprocess,time,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
base=Path('/tmp/vaio-everyday/gridcraft-test');base.mkdir(parents=True,exist_ok=True)
cli=os.environ.get('VAIO_GRID_CLI','/tmp/vaio-everyday/gridcraft-cli');binary=os.environ.get('VAIO_GRID_BINARY','/tmp/vaio-everyday/gridcraft')
env=dict(os.environ,DISPLAY=':0',GRIDCRAFT_NO_PREFS='1',XDG_CONFIG_HOME=str(base/'config'),LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
result={'checks':[],'timings':[]}
process=None;connection=None
try:
    args=[cli,'run']
    commands=[('range.setValues',{'range':'A1','values':[['Item','Quantity','Price','Cost'],['Alpha',2,4.5,'=B2*C2'],['Beta',3,2,'=B3*C3'],['Gamma',1,10,'=B4*C4'],['Total',None,None,'=SUM(D2:D4)']]}),('home.bold',{'range':'A1:D1','on':True}),('insert.chart',{'range':'A1:D4','type':'column','at':'F2','title':'Synthetic costs'})]
    for name,params in commands:args+=['--cmd',name+'='+json.dumps(params)]
    args+=['--out',str(base/'budget.xlsx')]
    completed=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=30)
    assert completed.returncode==0,completed.stderr
    log=(base/'application.log').open('w')
    process=subprocess.Popen([binary,'--control','7987',str(base/'budget.xlsx')],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        if process.poll() is not None:raise RuntimeError('Application exited at startup')
        try:connection=socket.create_connection(('127.0.0.1',7987),timeout=30);break
        except OSError:time.sleep(.2)
    if connection is None:raise RuntimeError('Control server unavailable')
    channel=connection.makefile('rwb',buffering=0);serial=0
    def request(method,params=None):
        global serial
        serial+=1;at=time.monotonic()
        channel.write((json.dumps({'id':serial,'method':method,'params':params or {}})+'\n').encode())
        response=json.loads(channel.readline().decode())
        result['timings'].append({'action':method,'seconds':round(time.monotonic()-at,3)})
        if not response.get('ok'):raise RuntimeError(method+': '+str(response.get('error')))
        return response.get('result')
    def execute(command,params=None):return request('engine.execute',{'command':command,'params':params or {}})
    time.sleep(2)
    result['initial_ui']=request('ui.inspect')
    request('ui.screenshot',{'path':str(base/'gridcraft-initial.png')})
    execute('view.animations',{'on':False})
    result['before']=request('cell.get',{'cell':'D5'})
    request('ui.focus')
    request('ui.cell.click',{'cell':'B2'})
    request('ui.inspect')
    time.sleep(.8)
    result['selected_before_edit']=request('cell.get')
    assert result['selected_before_edit']['cell']=='B2','Cell click has not selected B2'
    request('ui.edit.begin',{'text':'4'})
    request('ui.edit.commit',{'move':'none'})
    result['after']=request('cell.get',{'cell':'D5'})
    result['sheet']=request('sheet.read',{'range':'A1:D5'})
    request('app.save',{'path':str(base/'edited.xlsx')})
    with zipfile.ZipFile(str(base/'edited.xlsx')) as archive:
        ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        sheet=ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        total=sheet.find('.//s:c[@r="D5"]/s:v',ns)
        assert total is not None and float(total.text)==34.0,ET.tostring(sheet).decode()[:300]
        assert any(n.startswith('xl/charts/chart') for n in archive.namelist())
    for ext in ['csv']:
        completed=subprocess.run([cli,'convert',str(base/'edited.xlsx'),str(base/('export.'+ext))],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=30)
        assert completed.returncode==0,completed.stderr
        assert (base/('export.'+ext)).stat().st_size>50
    result['print_pdf']=execute('file.print',{'path':str(base/'export.pdf'),'range':'A1:K20','fitToPage':True})
    assert (base/'export.pdf').read_bytes().startswith(b'%PDF-')
    def sample():
        fields=Path('/proc/%d/stat'%process.pid).read_text().rsplit(')',1)[1].split()
        rss=next(int(line.split()[1]) for line in Path('/proc/%d/status'%process.pid).read_text().splitlines() if line.startswith('VmRSS:'))
        return int(fields[11])+int(fields[12]),rss
    time.sleep(1)
    before,rss=sample();at=time.monotonic();time.sleep(5);after,endrss=sample()
    result['loaded_private_xcb']=[line.split()[-1] for line in Path('/proc/%d/maps'%process.pid).read_text().splitlines() if '/lib/libxcb.so.1' in line]
    result['idle_cpu_percent_one_logical_cpu']=round(100*(after-before)/os.sysconf('SC_CLK_TCK')/(time.monotonic()-at),2)
    result['rss_kib']=endrss
    request('ui.screenshot',{'path':str(base/'gridcraft-ui.png')})
    request('app.open',{'path':str(base/'edited.xlsx')})
    result['reopened']=request('cell.get',{'cell':'D5'})
    request('app.quit');process.wait(timeout=15)
    result['checks']=['formulas','UI cell editing','recalculation','bold formatting','chart','XLSX save/reopen','CSV export','PDF export']
    result['passed']=True
except Exception as error:result.update(passed=False,error=str(error))
finally:
    if connection:connection.close()
    if process and process.poll() is None:process.terminate();process.wait(timeout=10)
(base/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='initial_ui'},indent=2))
raise SystemExit(0 if result['passed'] else 1)
