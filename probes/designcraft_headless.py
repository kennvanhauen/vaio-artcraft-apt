#!/usr/bin/env python3
"""Original, modest page-layout and MCP workflow on the real i386 VAIO."""
import json, os, select, subprocess, time, struct, zlib, zipfile
from pathlib import Path
base=Path('/tmp/vaio-designcraft-test');base.mkdir(parents=True,exist_ok=True)
cli=os.environ.get('VAIO_DESIGN_CLI',str(base/'designcraft-cli'))
env=dict(os.environ,DESIGNCRAFT_NO_PREFS='1',DESIGNCRAFT_CONFIG_DIR=str(base/'headless-profile'))
for key in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY'):env.pop(key,None)
result={'checks':[],'timings':[],'display_variables_absent':all(k not in env for k in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY'))}
def png():
    def chunk(k,b):return struct.pack('!I',len(b))+k+b+struct.pack('!I',zlib.crc32(k+b)&0xffffffff)
    raw=b''.join(b'\0'+bytes(v for x in range(160) for v in (30+x//3,80+y//2,120+x//4)) for y in range(80))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',160,80,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
(base/'original.png').write_bytes(png())
(base/'import.rtf').write_text(r'{\rtf1\ansi Original imported copy.\par Make, mend, and share.}')
process=None
try:
    process=subprocess.Popen([cli,'mcp','--automation-read-root',str(base),'--automation-write-root',str(base)],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(base/'headless-mcp.log').open('w'),universal_newlines=True,bufsize=1)
    serial=0
    def rpc(method,params):
        global serial
        serial+=1;at=time.monotonic();process.stdin.write(json.dumps({'jsonrpc':'2.0','id':serial,'method':method,'params':params})+'\n');process.stdin.flush()
        if not select.select([process.stdout],[],[],60)[0]:raise RuntimeError('MCP timeout: '+method)
        reply=json.loads(process.stdout.readline());result['timings'].append({'action':method,'seconds':round(time.monotonic()-at,3)})
        if 'error' in reply:raise RuntimeError(str(reply))
        return reply['result']
    def tool(name,args=None):
        r=rpc('tools/call',{'name':name,'arguments':args or {}})
        if r.get('isError'):raise RuntimeError(name+': '+str(r))
        return json.loads(next(c['text'] for c in r['content'] if c['type']=='text'))
    def execute(c,p=None):return tool('execute',{'command':c,'params':p or {}})
    result['initialize']=rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'vaio-verification','version':'1'}})
    tool('new_document',{'width':420,'height':595,'pages':3,'facingPages':False,'margins':30,'title':'The Repair Club — original brochure','primaryTextFrame':False})
    execute('swatch.create',{'name':'Club teal','color':'#19596b'})
    execute('style.paragraph.create',{'name':'Club heading','chars':{'fontFamily':'Source Sans 3','fontStyle':'Bold','size':26,'fill':'Club teal'},'para':{'spaceAfter':8}})
    execute('style.paragraph.create',{'name':'Club body','chars':{'fontFamily':'Source Serif 4','size':12},'para':{'spaceAfter':5}})
    heading=execute('frame.create',{'spread':0,'rect':[30,30,390,100],'content':'text','text':'THE REPAIR CLUB','caret':True})
    execute('style.paragraph.apply',{'name':'Club heading'})
    execute('file.place',{'path':str(base/'original.png'),'spread':0,'x':30,'y':110,'width':360})
    body=execute('frame.create',{'spread':0,'rect':[30,310,390,550],'content':'text','text':'Make, mend, and share.\nAn original three-page brochure created on the Sony VAIO.\nSaturday workshop: bring a small item and learn a useful skill.','caret':True})
    execute('style.paragraph.apply',{'name':'Club body'})
    a=execute('frame.create',{'spread':1,'rect':[30,30,200,270],'content':'text','text':'A PRACTICAL WORKSHOP\n'+('Work together, keep good notes, and pass on what you learn. '*9),'caret':True})
    execute('style.paragraph.apply',{'name':'Club body'})
    b=execute('frame.create',{'spread':1,'rect':[220,30,390,270],'content':'text','caret':False})
    result['thread']=execute('text.thread',{'from':a['id'],'to':b['id']})
    t=execute('frame.create',{'spread':1,'rect':[30,300,390,530],'content':'text','text':'','caret':True})
    execute('table.insert',{'rows':3,'cols':2,'headerRows':1,'width':330})
    for row,values in enumerate([('SESSION','TIME'),('Welcome','10:00'),('Make and mend','10:30'),('Share results','12:00')]):
        for col,text in enumerate(values):execute('table.setCell',{'row':row,'col':col,'text':text})
    result['table']=execute('table.get')
    execute('file.place',{'path':str(base/'import.rtf'),'page':3,'rect':[30,30,390,350]})
    execute('edit.undo');execute('edit.redo')
    result['preflight']=execute('preflight.run',{'minPpi':25})
    tool('save_document',{'path':str(base/'original.designcraft')})
    result['original']=tool('inspect_document')
    assert result['original']['pageCount']==3,result['original'].keys()
    assert 'THE REPAIR CLUB' in json.dumps(result['original'])
    for command,ext in [('file.exportIdml','idml'),('file.exportPdf','pdf'),('file.exportEpub','epub'),('file.exportPptx','pptx'),('file.exportHtml','html')]:
        result['export_'+ext]=execute(command,{'path':str(base/('brochure.'+ext))})
        assert (base/('brochure.'+ext)).stat().st_size>80
    for ext in ('txt','rtf'):
        execute('file.exportText',{'path':str(base/('body.'+ext)),'story':body['story']})
    for ext in ('designcraft','idml'):
        tool('open_document',{'path':str(base/('original.designcraft' if ext=='designcraft' else 'brochure.idml'))})
        d=tool('inspect_document');assert d['pageCount']==3 and 'THE REPAIR CLUB' in json.dumps(d)
        result['reopen_'+ext]={'pages':d['pageCount'],'stories':len(d['stories'])}
    rendered=subprocess.run([cli,'run','--in',str(base/'original.designcraft'),'--all-pages',str(base/'pages')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=90)
    assert rendered.returncode==0,rendered.stderr
    assert len(list((base/'pages').glob('*.png')))==3
    denied=rpc('tools/call',{'name':'open_document','arguments':{'path':'/etc/hostname'}})
    assert denied.get('isError'), 'Read root failed'
    denied=rpc('tools/call',{'name':'save_document','arguments':{'path':'/tmp/designcraft-outside-root.designcraft'}})
    assert denied.get('isError'), 'Write root failed'
    for ext,required in [('idml','designmap.xml'),('epub','META-INF/container.xml'),('pptx','ppt/presentation.xml')]:
        with zipfile.ZipFile(str(base/('brochure.'+ext))) as z:assert required in z.namelist() and z.testzip() is None
    p=subprocess.run(['pdftotext',str(base/'brochure.pdf'),'-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=30)
    assert p.returncode==0 and 'THE REPAIR CLUB' in p.stdout,p.stderr
    result['checks']=['no-display MCP','original three pages','styles','image placement','manual two-frame threading','table','RTF import','undo/redo','preflight','native/IDML save-reopen','PDF/EPUB/PPTX/HTML/TXT/RTF export','ZIP integrity','independent PDF text','read/write root confinement']
    result['passed']=True
except Exception as e:result.update(passed=False,error=str(e))
finally:
    if process:
        process.stdin.close()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
(base/'headless-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('original','timings','table')},indent=2))
raise SystemExit(0 if result.get('passed') else 1)
