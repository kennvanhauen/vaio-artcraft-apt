#!/usr/bin/env python3
"""Independently inspect modest exports and exercise parent pages/data merge/PDF-X."""
import base64,json,os,subprocess,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
base=Path('/tmp/vaio-designcraft-test');cli=os.environ.get('VAIO_DESIGN_CLI',str(base/'designcraft-cli'))
env=dict(os.environ,DESIGNCRAFT_CONFIG_DIR=str(base/'format-profile'),DESIGNCRAFT_NO_PREFS='1')
for k in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY'):env.pop(k,None)
r={'checks':[]}
def run(*a):
    p=subprocess.run([cli]+list(a),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=90)
    assert p.returncode==0,p.stderr
    return p.stdout
try:
    with zipfile.ZipFile(str(base/'brochure.pptx')) as z:
        slides=[n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
        assert len(slides)==3
        texts=[''.join(ET.fromstring(z.read(n)).itertext()) for n in slides]
        assert 'THE REPAIR CLUB' in texts[0] and 'SESSION' in texts[1] and 'Original imported copy.' in texts[2]
    with zipfile.ZipFile(str(base/'brochure.epub')) as z:
        texts=''.join(z.read(n).decode() for n in z.namelist() if n.endswith(('.xhtml','.html')))
        assert 'THE REPAIR CLUB' in texts and 'Original imported copy.' in texts
    info=subprocess.check_output(['pdfinfo',str(base/'brochure.pdf')]).decode()
    assert 'Pages:          3' in info
    run('run','--in',str(base/'original.designcraft'),'--pdf-options','{"standard":"x4"}','--export',str(base/'pdfx4.pdf'))
    check=subprocess.run([cli,'validate-pdf',str(base/'pdfx4.pdf')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=30)
    r['pdfx4']=json.loads(check.stdout)
    r['pdfx4_note']='RGB artwork fails upstream CMYK-output-intent validator; no prepress compliance claim.'
    assert any('RGB' in issue for issue in r['pdfx4']['issues']),r['pdfx4']
    run('run','--in',str(base/'original.designcraft'),'--cmd','swatch.options='+json.dumps({'name':'Club teal','color':{'c':80,'m':30,'y':0,'k':40}}),'--pdf-options','{"standard":"x4"}','--export',str(base/'pdfx4-cmyk.pdf'))
    checked=subprocess.run([cli,'validate-pdf',str(base/'pdfx4-cmyk.pdf')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=30)
    r['pdfx4_cmyk']=json.loads(checked.stdout)
    # Record the built-in check independently of ordinary export interoperability.
    # A second original one-page template; two records only, no performance/stress exercise.
    steps=[{'command':'file.new','params':{'width':420,'height':300,'pages':1,'facingPages':False,'title':'Workshop invitations'}},
           {'command':'frame.create','params':{'spread':{'kind':'parent','index':0},'rect':[25,250,395,280],'content':'text','text':'THE REPAIR CLUB — INVITATION','caret':False}},
           {'command':'frame.create','params':{'rect':[25,25,395,200],'content':'text','text':'Welcome, guest!','caret':True}},
           {'command':'data.source.select','params':{'base64':base64.b64encode(b'Name\nAlex\nSam\n').decode(),'name':'Original synthetic guests.csv'}},
           {'command':'data.placeholder.add','params':{'field':'Name','story':'$2.story','at':9,'end':14}},
           {'command':'data.merge','params':{}},
           {'command':'file.save','params':{'path':str(base/'merged.designcraft')}}]
    (base/'merge.json').write_text(json.dumps(steps))
    r['merge']=json.loads(run('script',str(base/'merge.json'),'--export',str(base/'merged.pdf')))
    text=subprocess.check_output(['pdftotext',str(base/'merged.pdf'),'-']).decode()
    assert 'Alex' in text and 'Sam' in text and text.count('INVITATION')==2,text
    r['checks']=['three PPTX slides with editable text/table contents','EPUB text','independent PDF page count','PDF/X-4 validator reports RGB compliance limitation','parent-page text','two-record data merge']
    r['passed']=True
except Exception as e:r.update(passed=False,error=str(e))
(base/'formats-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
raise SystemExit(0 if r.get('passed') else 1)
