#!/usr/bin/env python3
"""Bounded original format/typography checks; no proprietary applications or fixtures."""
import json, os, subprocess, time
from pathlib import Path
base=Path('/tmp/vaio-vectorcraft-test')
cli=os.environ.get('VAIO_VECTOR_CLI',str(base/'vectorcraft-cli'))
env=dict(os.environ,VECTORCRAFT_NO_PREFS='1',XDG_CONFIG_HOME=str(base/'format-config'),XDG_DATA_HOME=str(base/'format-data'))
for key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY'):env.pop(key,None)
result={'checks':[],'exports':[]}
def run(*args):
    p=subprocess.run([cli]+list(args),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=90)
    if p.returncode:raise RuntimeError(str(args)+': '+p.stderr[:1200])
    return p.stdout
try:
    commands=[('layer.new',{'name':'Multilingual original'}),
              ('text.create',{'x':35,'y':145,'text':'日本語の修理','font':'BIZ UDPGothic','size':14,'color':'#12364e'}),
              ('text.create',{'x':270,'y':170,'text':'مرحبا بالعالم','font':'Noto Sans Arabic','size':14,'color':'#12364e'}),
              ('text.create',{'x':250,'y':285,'text':'Ελληνικά — café','font':'Inter','size':14,'color':'#12364e'}),
              ('text.create',{'x':250,'y':320,'text':'ქართული','font':'Noto Sans Georgian','size':14,'color':'#12364e'}),
              ('paint.setFill',{'gradient':{'kind':'radial','stops':[{'offset':0,'color':'#ffd56f'},{'offset':1,'color':'#dc7645'}]}}),
              ('shape.ellipse',{'x':350,'y':220,'width':90,'height':50}),
              ('object.setProps',{'opacity':75,'name':'Translucent gradient'}),
              ('select.none',{})]
    args=['run','--in',str(base/'original.vectorcraft')]
    for command,params in commands:args+=['--cmd',command,'--params',json.dumps(params)]
    args+=['--export',str(base/'advanced.vectorcraft')]
    run(*args)
    result['advanced_info']=json.loads(run('info',str(base/'advanced.vectorcraft')))
    assert all(not f.get('missing') and f.get('missingGlyphs',0)==0 for f in result['advanced_info']['fonts'])
    for ext in ['svgz','jpg','webp','gif','tiff','bmp','tga','psd','ai','emf','wmf','txt']:
        path=base/('advanced.'+ext);at=time.monotonic()
        output=run('convert',str(base/'advanced.vectorcraft'),str(path))
        assert path.stat().st_size>10
        result['exports'].append({'extension':ext,'bytes':path.stat().st_size,'seconds':round(time.monotonic()-at,3),'result':output[:1600]})
    assert 'Ελληνικά' in (base/'advanced.txt').read_text()
    (base/'legacy.drawcraft').write_bytes((base/'advanced.vectorcraft').read_bytes())
    result['legacy_info']=json.loads(run('info',str(base/'legacy.drawcraft')))
    assert result['legacy_info']['info']['objects']==result['advanced_info']['info']['objects']
    for ext in ['svgz','ai','psd','emf','wmf']:
        result[ext+'_reopen']=json.loads(run('info',str(base/('advanced.'+ext))))
    result['checks']=['Japanese/Arabic/Greek/Georgian/Latin font resolution','radial gradient/transparency','12 additional export formats','five additional format reopen checks','legacy extension']
    result['passed']=True
except Exception as error:result.update(passed=False,error=str(error))
(base/'formats-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('advanced_info','legacy_info') and not k.endswith('_reopen')},indent=2))
raise SystemExit(0 if result.get('passed') else 1)
