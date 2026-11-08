#!/usr/bin/env python3
"""Bounded synthetic review/references/math/merge/recovery checks on the real VAIO."""
import json,subprocess,time,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from vaio_test_support import App
base=Path('/tmp/vaio-everyday/wordcraft-advanced');base.mkdir(parents=True,exist_ok=True)
cli='/usr/bin/wordcraft-vaio-cli';result={'checks':[]};app=None
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
def run(*args):
    p=subprocess.run([cli]+list(args),stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=45)
    if p.returncode:raise RuntimeError(args[0]+': '+p.stderr[:700])
    return p.stdout
def commands(items,path,file=None):
    args=['run','--author','Synthetic VAIO Reviewer']
    if file:args+=['--file',str(file)]
    for command,params in items:args+=['--cmd',command+'='+json.dumps(params)]
    args+=['--save',str(path)];run(*args)
def xml(path):
    with zipfile.ZipFile(str(path)) as z:return ET.fromstring(z.read('word/document.xml')),z.namelist()
try:
    (base/'source.md').write_text('# Review and references\n\nA synthetic paragraph for review. A mispellled word.\n\n## Project details\n\nA short second section.\n')
    run('convert',str(base/'source.md'),str(base/'source.docx'))
    reviewed=base/'reviewed.docx'
    commands([('caret.docEnd',{}),('review.newComment',{'text':'Original synthetic comment'}),
              ('review.trackChanges',{'value':True}),('text.insert',{'text':' Tracked addition marker.'}),
              ('review.trackChanges',{'value':False}),('references.footnote',{'text':'Synthetic footnote marker.'}),
              ('select.range',{'anchor':{'block':0,'off':0},'focus':{'block':0,'off':0}}),
              ('caret.docEnd',{}),('insert.equation',{'latex':'x^2 + y^2 = z^2','edit':False}),
              ('caret.docStart',{}),('references.toc',{'levels':2,'title':'Synthetic contents'}),
              ('insert.pageNumber',{'position':'bottom'}),('layout.columns',{'count':2,'apply':'document'})],reviewed,base/'source.docx')
    doc,names=xml(reviewed)
    assert doc.findall('.//w:ins',ns),'Tracked insertion missing'
    assert doc.findall('.//m:oMath',ns),'Equation missing'
    assert 'word/comments.xml' in names and 'word/footnotes.xml' in names
    assert any(e.get('{'+ns['w']+'}num')=='2' for e in doc.findall('.//w:cols',ns))
    assert any('TOC' in (e.text or '') for e in doc.findall('.//w:instrText',ns))
    for action,present in [('acceptAll',True),('rejectAll',False)]:
        output=base/(action+'.docx');commands([('review.'+action,{})],output,reviewed)
        d,_=xml(output);assert not d.findall('.//w:ins',ns)
        assert ('Tracked addition marker.' in run('text',str(output)))==present
    run('convert',str(reviewed),str(base/'reviewed.pdf'),'--markup')
    result['checks']+=['tracked changes save/reopen','accept/reject changes','comments','footnote','equation','table of contents','page numbers','two-column layout','PDF with review markup']
    merged=base/'merged.docx'
    commands([('text.insert',{'text':'Dear '}),('mailings.insertField',{'field':'Name'}),
              ('text.insert',{'text':', your synthetic letter.'}),
              ('mailings.recipients',{'rows':[{'Name':'Alpha Test'},{'Name':'Beta Test'}]}),
              ('mailings.finish',{'path':str(merged)})],base/'merge-template.docx')
    text=run('text',str(merged));assert 'Alpha Test' in text and 'Beta Test' in text
    result['checks'].append('two-recipient mail merge')
    app=App(base/'gui',7989,file=reviewed)
    time.sleep(1)
    result['spelling']=app.execute('review.spelling')
    app.execute('ui.tab',{'name':'Review'});app.request('ui.screenshot',{'path':str(base/'review-ui.png')})
    app.execute('caret.docEnd');app.execute('insert.equation',{'linear':'a=b+c','edit':True})
    app.execute('equation.type',{'text':'+1'});result['equation_gui']=app.execute('equation.get')
    app.request('ui.screenshot',{'path':str(base/'equation-ui.png')})
    app.execute('equation.exit');app.execute('file.save',{'path':str(base/'gui-edited.docx')})
    d,_=xml(base/'gui-edited.docx');assert len(d.findall('.//m:oMath',ns))>=2
    result['checks']+=['GUI advanced document rendering','GUI equation editing','proofing command']
    app.close();app=None
    # Only a disposable process/profile is terminated; the desktop/session stay running.
    app=App(base/'recovery',7990,prefs=True)
    app.execute('file.new');app.execute('text.insert',{'text':'Unsaved synthetic recovery marker.'})
    until=time.monotonic()+22
    while time.monotonic()<until:
        state=app.execute('file.recover')
        if state.get('documents') and not state.get('busy'):break
        time.sleep(.5)
    assert state.get('enabled') and state.get('documents'),state
    profile=app.profile
    app.process.kill();app.process.wait(timeout=10);app.close();app=None
    app=App(base/'recovery',7990,prefs=True,profile=profile)
    until=time.monotonic()+15
    while time.monotonic()<until:
        # Startup already queues an asynchronous recovery scan. Poll its state;
        # another refresh races that scan and correctly returns "busy".
        state=app.execute('file.recover')
        if state.get('documents') and not state.get('busy'):break
        time.sleep(.5)
    assert state.get('documents'),state
    app.execute('file.recover',{'restore':state['documents'][0]['id']})
    until=time.monotonic()+12
    while time.monotonic()<until:
        state=app.execute('file.recover')
        if not state.get('busy'):break
        time.sleep(.3)
    recovered=base/'recovered.docx';app.execute('file.save',{'path':str(recovered)})
    assert 'Unsaved synthetic recovery marker.' in run('text',str(recovered))
    result['checks'].append('unsaved draft recovery after disposable-process termination')
    result['passed']=True
except Exception as error:result.update(passed=False,error=str(error))
finally:
    if app:app.close()
(base/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));raise SystemExit(0 if result.get('passed') else 1)
