#!/usr/bin/env python3
"""Original small drafting workflow on the VAIO without a display."""
import json,os,re,select,subprocess,time
from pathlib import Path
base=Path('/tmp/vaio-cadcraft-test');cli=os.environ.get('VAIO_CAD_CLI',str(base/'cadcraft-cli'))
env=dict(os.environ,CADCRAFT_CONFIG_DIR=str(base/'headless-profile'),XDG_CONFIG_HOME=str(base/'headless-config'),XDG_DATA_HOME=str(base/'headless-data'))
for k in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY'):env.pop(k,None)
r={'checks':[],'display_variables_absent':all(k not in env for k in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY'))};p=None;serial=0
try:
 p=subprocess.Popen([cli,'mcp'],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(base/'mcp.log').open('w'),universal_newlines=True,bufsize=1)
 def rpc(m,a):
  global serial
  serial+=1;p.stdin.write(json.dumps({'jsonrpc':'2.0','id':serial,'method':m,'params':a})+'\n');p.stdin.flush()
  if not select.select([p.stdout],[],[],90)[0]:raise RuntimeError('MCP timeout '+m)
  out=json.loads(p.stdout.readline());assert 'error' not in out,out
  return out['result']
 def tool(n,a=None):
  q=rpc('tools/call',{'name':n,'arguments':a or {}});assert not q.get('isError'),q
  text=next(c['text'] for c in q['content'] if c['type']=='text')
  try:return json.loads(text)
  except ValueError:return text
 def cmd(n,a=None):return tool('execute',{'command':n,'params':a or {}})
 rpc('initialize',{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'vaio-cad-port-check','version':'1'}})
 commands=tool('list_commands');r['command_count']=len(commands) if isinstance(commands,list) else len(commands.get('commands',[]))
 tool('new_drawing',{'metric':True});cmd('setvar',{'name':'INSUNITS','value':4})
 cmd('layer.new',{'name':'Outline','color':'white','current':True})
 outline=cmd('rectang',{'p1':[0,0],'p2':[120,80],'fillet':5})
 cmd('layer.new',{'name':'Holes','color':'cyan','current':True})
 hole=cmd('circle',{'center':[12,12],'radius':4})['handle']
 cmd('block',{'name':'Mounting hole','base':[12,12],'handles':[hole],'keep':'convert'})
 for at in [[108,12],[12,68],[108,68]]:cmd('insert',{'name':'Mounting hole','at':at})
 cmd('layer.new',{'name':'Center','color':'red','current':True})
 line=cmd('line',{'points':[[-5,40],[125,40]]})['handles'][0];cmd('gchorizontal',{'h1':line})
 cmd('line',{'points':[[60,-5],[60,85]]})
 cmd('layer.new',{'name':'Dimensions','color':'green','current':True})
 cmd('dimlinear',{'p1':[0,0],'p2':[120,0],'at':[60,-13]});cmd('dimlinear',{'p1':[120,0],'p2':[120,80],'at':[139,40]})
 cmd('layer.new',{'name':'Notes','color':'white','current':True})
 title=cmd('text',{'at':[0,100],'text':'REPAIR CLUB — MOUNTING PLATE','height':5})['handle']
 cmd('mtext',{'at':[0,-25],'text':'Original CADCraft VAIO example\\P120 x 80 mm; four mounting holes\\PNot a production engineering drawing.','height':3.5,'width':155})
 assert cmd('lisp',{'code':'(+ 20 22)'})['value']=='42'
 cmd('move',{'handles':[title],'delta':[2,0]});cmd('undo');cmd('redo')
 cmd('zoom',{'mode':'extents'})
 tool('save',{'path':str(base/'repair-plate.dxf')})
 r['drawing']=tool('inspect_drawing',{'entities':True,'limit':100});assert r['drawing']['counts'].get('Dimension',0)>=2,r['drawing']
 assert 'REPAIR CLUB' in json.dumps(r['drawing'],ensure_ascii=False)
 r['handles']={'outline':outline,'heading':title,'centerline':line};(base/'handles.json').write_text(json.dumps(r['handles']))
 for ext in ['svg','pdf','png','dwg']:
  out=subprocess.run([cli,'convert',str(base/'repair-plate.dxf'),str(base/('repair-plate.'+ext))],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=120)
  assert out.returncode==0,(ext,out.stderr);assert (base/('repair-plate.'+ext)).stat().st_size>50
  r['export_'+ext]={'bytes':(base/('repair-plate.'+ext)).stat().st_size,'notes':out.stderr.strip()[:1500]}
 tool('open',{'path':str(base/'repair-plate.dxf')});native=tool('inspect_drawing',{'entities':True,'limit':100});assert 'REPAIR CLUB' in json.dumps(native,ensure_ascii=False)
 tool('open',{'path':str(base/'repair-plate.dwg')});dwg=tool('inspect_drawing',{'entities':True,'limit':100});assert 'REPAIR CLUB' in json.dumps(dwg,ensure_ascii=False);r['own_dwg_counts']=dwg['counts']
 tool('open',{'path':str(base/'repair-plate.dxf')});cmd('layout.new',{'name':'A4 workshop','viewport':True});cmd('pagesetup',{'layout':'A4 workshop','paper':'A4','landscape':True})
 cmd('plot',{'path':str(base/'a4-workshop.pdf'),'layout':'A4 workshop','paper':'A4','landscape':True,'fit':True})
 tool('save',{'path':str(base/'repair-plate-layout.dxf')});r['layouts']=cmd('layout.list')
 # Independent ASCII DXF group-pair checks, rather than only an own-code round trip.
 lines=(base/'repair-plate.dxf').read_text().splitlines();pairs=list(zip([x.strip() for x in lines[0::2]],[x.strip() for x in lines[1::2]]))
 assert ('0','LWPOLYLINE') in pairs and ('0','INSERT') in pairs and ('0','DIMENSION') in pairs
 pdf=subprocess.check_output(['pdfinfo',str(base/'a4-workshop.pdf')]).decode();assert re.search(r'^Pages:\s+1$',pdf,re.M);r['pdfinfo']=pdf
 r['checks']=['no-display MCP','original metric drawing','rounded rectangle','block with four inserts','layers','center lines and horizontal constraint','two dimensions','text/MTEXT','LISP expression','move undo/redo','DXF reopen','SVG/PDF/PNG export','own synthetic DWG round trip','paper-space viewport and A4 PDF plot','independent DXF groups and PDF page check'];r['passed']=True
except Exception as e:r.update(passed=False,error=repr(e))
finally:
 if p:
  p.stdin.close()
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=10)
(base/'headless-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['drawing','pdfinfo']},indent=2));raise SystemExit(0 if r.get('passed') else 1)
