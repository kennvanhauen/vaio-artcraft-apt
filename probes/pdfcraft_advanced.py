#!/usr/bin/env python3
"""Small original forms/redaction/crypto/OCR workflows; bounded single-page OCR."""
import json,os,subprocess,time
from pathlib import Path
base=Path('/tmp/vaio-everyday/pdfcraft-advanced');base.mkdir(parents=True,exist_ok=True,mode=0o700)
cli=os.environ.get('VAIO_PDF_CLI','/tmp/vaio-everyday/pdfcraft-cli')
source='/tmp/vaio-everyday/allowed-pdf-test.pdf'
env=dict(os.environ,PDFCRAFT_MODELS='/tmp/vaio-everyday',LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
if os.environ.get('VAIO_PDF_INSTALLED'):env.pop('PDFCRAFT_MODELS',None)
result={'checks':[],'timings':[]}
def run(*args,timeout=45):
    at=time.monotonic();p=subprocess.run([cli]+list(args),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=timeout)
    result['timings'].append({'action':args[0],'seconds':round(time.monotonic()-at,3)})
    if p.returncode:raise RuntimeError(args[0]+': '+p.stderr[:700])
    return p.stdout
def tools(name,steps,timeout=45):
    path=base/(name+'.json');path.write_text(json.dumps([{'tool':tool,'args':args} for tool,args in steps]))
    return json.loads(run('run','--script',str(path),'--root',str(base.parent),'--report',timeout=timeout))
try:
    forms=base/'forms.pdf'
    tools('forms',[('doc_open',{'path':source}),('form_add_field',{'doc':1,'page':1,'type':'text','name':'SyntheticName','rect':[40,260,260,290]}),
                   ('form_add_field',{'doc':1,'page':1,'type':'checkbox','name':'SyntheticCheck','rect':[40,300,60,320]}),
                   ('form_fill',{'doc':1,'values':{'SyntheticName':'Original VAIO form test','SyntheticCheck':True}}),
                   ('doc_save',{'doc':1,'path':str(forms)})])
    result['forms']=json.loads(run('info',str(forms)))
    assert result['forms']['fields']==2,result['forms']
    report=tools('read-forms',[('doc_open',{'path':str(forms)}),('form_fields',{'doc':1})])
    serialized=json.dumps(report);assert 'Original VAIO form test' in serialized and 'SyntheticCheck' in serialized
    result['checks'].append('form creation/filling and saved-field round trip')
    redacted=base/'redacted.pdf'
    tools('redact',[('doc_open',{'path':source}),('redact_mark',{'doc':1,'pages':[1],'find':'Original VAIO PDF test page 1'}),
                    ('redact_apply',{'doc':1}),('doc_save',{'doc':1,'path':str(redacted)})])
    text=run('text',str(redacted));assert 'test page 1' not in text and 'test page 2' in text
    result['checks'].append('applied redaction removes synthetic target text')
    protected=base/'protected.pdf';plain=base/'unprotected.pdf'
    # Explicitly public synthetic test password, never a user's credential.
    tools('protect',[('doc_open',{'path':source}),('doc_protect',{'doc':1,'open_password':'synthetic-fixture-only','compatibility':'aes-256'}),
                     ('doc_save',{'doc':1,'path':str(protected)})])
    tools('unprotect',[('doc_open',{'path':str(protected),'password':'synthetic-fixture-only'}),
                       ('doc_unprotect',{'doc':1}),('doc_save',{'doc':1,'path':str(plain)})])
    assert 'test page 3' in run('text',str(plain))
    result['checks'].append('AES-256 password save/reopen/decrypt round trip')
    page=base/'scan.png';scan=base/'scan.pdf';recognized=base/'recognized.pdf'
    run('render',source,'--page','1','--dpi','144','--out',str(page))
    tools('scan',[('doc_create',{'from':'images','paths':[str(page)],'dpi':144}),('doc_save',{'doc':1,'path':str(scan)})])
    assert not run('text',str(scan)).strip(),'OCR input must be image-only'
    tools('ocr',[('doc_open',{'path':str(scan)}),('ocr_recognize',{'doc':1,'pages':[1],'dpi':144}),
                 ('doc_save',{'doc':1,'path':str(recognized)})],timeout=90)
    result['ocr_text']=run('text',str(recognized)).strip()
    assert 'VAIO' in result['ocr_text'] and 'Synthetic' in result['ocr_text'],result['ocr_text']
    result['checks'].append('single image-only page recognized into searchable text')
    result['passed']=True
except Exception as error:result.update(passed=False,error=str(error))
(base/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));raise SystemExit(0 if result.get('passed') else 1)
