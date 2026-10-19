#!/usr/bin/env python3
"""Small original PDF workflows, isolated settings, no OCR downloads or print jobs."""
import json,os,shutil,subprocess,time
from pathlib import Path
base=Path('/tmp/vaio-everyday/pdfcraft-test');base.mkdir(parents=True,exist_ok=True,mode=0o700)
(base/'runtime').mkdir(exist_ok=True,mode=0o700)
source=base/'original.pdf';shutil.copyfile('/tmp/vaio-everyday/allowed-pdf-test.pdf',str(source))
cli=os.environ.get('VAIO_PDF_CLI','/tmp/vaio-everyday/pdfcraft-cli');binary=os.environ.get('VAIO_PDF_BINARY','/tmp/vaio-everyday/pdfcraft')
env=dict(os.environ,DISPLAY=':0',PDFCRAFT_RENDERER='gl',XDG_CONFIG_HOME=str(base/'config'),XDG_DATA_HOME=str(base/'data'),XDG_CACHE_HOME=str(base/'cache'),XDG_RUNTIME_DIR=str(base/'runtime'),LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
result={'timings':[]};process=None

def run(*args):
    at=time.monotonic()
    p=subprocess.run([cli]+list(args),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=40)
    result['timings'].append({'action':args[0],'seconds':round(time.monotonic()-at,3)})
    if p.returncode:raise RuntimeError('CLI '+args[0]+': '+p.stderr[:1000])
    return p.stdout

def ui(method,*args):return json.loads(run('ui','--control',str(base/'control.json'),method,*args))
try:
    result['info']=json.loads(run('info',str(source)));assert result['info']['pages']==3
    result['text_markers']=all(('test page %d'%n) in run('text',str(source)) for n in [1,2,3])
    assert result['text_markers']
    run('render',str(source),'--page','1','--dpi','72','--out',str(base/'page.png'))
    assert (base/'page.png').read_bytes().startswith(b'\x89PNG')
    run('extract',str(source),'--pages','2','--out',str(base/'extracted.pdf'))
    assert json.loads(run('info',str(base/'extracted.pdf')))['pages']==1
    run('combine',str(source),str(base/'extracted.pdf'),'--out',str(base/'combined.pdf'))
    assert json.loads(run('info',str(base/'combined.pdf')))['pages']==4
    script=[{'tool':'doc_open','args':{'path':str(source)}},
        {'tool':'comment_add','args':{'doc':1,'page':1,'type':'note','at':[80,110],'contents':'Original synthetic review note','author':'VAIO test'}},
        {'tool':'page_rotate','args':{'doc':1,'pages':[2],'degrees':90}},
        {'tool':'doc_save','args':{'doc':1,'path':str(base/'annotated.pdf')}}]
    (base/'steps.json').write_text(json.dumps(script))
    run('run','--script',str(base/'steps.json'),'--root',str(base),'--report')
    result['annotated_info']=json.loads(run('info',str(base/'annotated.pdf')))
    assert result['annotated_info']['pages']==3 and result['annotated_info']['annotations']==1
    log=(base/'application.log').open('w')
    process=subprocess.Popen([binary,'--control',str(base/'control.json'),str(base/'annotated.pdf')],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
    deadline=time.monotonic()+35
    while time.monotonic()<deadline and not (base/'control.json').exists():
        if process.poll() is not None:raise RuntimeError('GUI exited during startup')
        time.sleep(.2)
    assert (base/'control.json').exists(),'Control endpoint unavailable'
    assert (base/'control.json').stat().st_mode & 0o077==0,'Control permissions too broad'
    time.sleep(1)
    result['state']=ui('state')
    ui('resize','width=1100','height=650')
    ui('screenshot','--out',str(base/'pdfcraft-ui.png'))
    def sample():
        fields=Path('/proc/%d/stat'%process.pid).read_text().rsplit(')',1)[1].split()
        rss=next(int(line.split()[1]) for line in Path('/proc/%d/status'%process.pid).read_text().splitlines() if line.startswith('VmRSS:'))
        return int(fields[11])+int(fields[12]),rss
    time.sleep(1);before,rss=sample();at=time.monotonic();time.sleep(5);after,endrss=sample()
    result['loaded_private_xcb']=[line.split()[-1] for line in Path('/proc/%d/maps'%process.pid).read_text().splitlines() if '/lib/libxcb.so.1' in line]
    result['idle_cpu_percent_one_logical_cpu']=round(100*(after-before)/os.sysconf('SC_CLK_TCK')/(time.monotonic()-at),2)
    result['rss_kib']=endrss
    ui('quit');process.wait(timeout=15)
    result['passed']=True
except Exception as error:result.update(passed=False,error=str(error))
finally:
    if process and process.poll() is None:process.terminate();process.wait(timeout=10)
(base/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='state'},indent=2));raise SystemExit(0 if result['passed'] else 1)
