#!/usr/bin/env python3
"""Original modest UI-design workflow on the VAIO, without a display."""
import json,os,select,subprocess,time,zipfile
from pathlib import Path
base=Path('/tmp/vaio-figcraft-test');base.mkdir(parents=True,exist_ok=True)
cli=os.environ.get('VAIO_FIG_CLI',str(base/'figcraft-cli'));env=dict(os.environ,FIGCRAFT_NO_SYSTEM_FONTS='1',XDG_CONFIG_HOME=str(base/'headless-config'),XDG_DATA_HOME=str(base/'headless-data'))
for k in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY'):env.pop(k,None)
r={'checks':[],'display_variables_absent':all(k not in env for k in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY'))};p=None
try:
 p=subprocess.Popen([cli,'mcp','--automation-read-root',str(base),'--automation-write-root',str(base)],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(base/'mcp.log').open('w'),universal_newlines=True,bufsize=1);serial=0
 def rpc(m,a):
  global serial
  serial+=1;p.stdin.write(json.dumps({'jsonrpc':'2.0','id':serial,'method':m,'params':a})+'\n');p.stdin.flush()
  if not select.select([p.stdout],[],[],60)[0]:raise RuntimeError('MCP timeout '+m)
  out=json.loads(p.stdout.readline());assert 'error' not in out,out
  return out['result']
 def tool(n,a=None):
  q=rpc('tools/call',{'name':n,'arguments':a or {}});assert not q.get('isError'),q
  text=next(c['text'] for c in q['content'] if c['type']=='text')
  try:return json.loads(text)
  except ValueError:return text
 def cmd(n,a=None):return tool('run_command',{'command':n,'params':a or {}})
 def node(kind,name,parent=None,x=0,y=0,w=100,h=100,text=None,**props):
  a={'type':kind,'name':name,'x':x,'y':y,'width':w,'height':h,'props':props}
  if parent is not None:a['parent']=parent
  if text is not None:a['text']=text
  return tool('create_node',a)['id']
 r['initialize']=rpc('initialize',{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'vaio-port-check','version':'1'}})
 r['command_count']=int(tool('list_commands').split()[0])
 home=node('frame','Repair Club — Home',x=0,y=0,w=320,h=480,fill='#f6f2e9',clip=True)
 title=node('text','Heading',home,20,22,280,35,'THE REPAIR CLUB',fontFamily='Inter',fontSize=22,fontStyle='Bold',fill='#155366')
 node('text','Subtitle',home,20,65,280,30,'Make, mend, and share.',fontFamily='Inter',fontSize=14,fill='#334155')
 stack=node('frame','Auto layout sessions',home,20,120,280,240,layout='vertical',gap=12,padding=12,fill='#ffffff',cornerRadius=12)
 for label,detail in [('Welcome','Saturday 10:00'),('Make and mend','Saturday 10:30'),('Share results','Saturday 12:00')]:
  row=node('frame',label,stack,w=256,h=56,layout='horizontal',gap=8,padding=10,fill='#e5f0ed',cornerRadius=8)
  node('text',label+' label',row,w=230,h=36,text=label+'\n'+detail,fontFamily='Inter',fontSize=13,fill='#155366')
 button=node('frame','Primary button',x=0,y=550,w=280,h=44,fill='#155366',cornerRadius=10,layout='horizontal',padding=12)
 node('text','Button label',button,w=240,h=25,text='View workshop',fontFamily='Inter',fontSize=15,fill='#ffffff')
 component=cmd('component.create',{'ids':[button]})['id']
 instance=cmd('instance.create',{'component':component,'parent':home,'x':20,'y':400})['id']
 details=node('frame','Repair Club — Workshop',x=360,y=0,w=320,h=480,fill='#f6f2e9',clip=True)
 node('text','Workshop title',details,20,25,280,45,'MAKE AND MEND',fontFamily='Inter',fontSize=23,fontStyle='Bold',fill='#155366')
 node('text','Workshop description',details,20,95,280,180,'Bring a small item.\nLearn one useful skill.\nShare your repair notes.\n\nOriginal VAIO interface-design example.',fontFamily='Inter',fontSize=17,fill='#334155')
 back=node('frame','Back button',details,20,400,280,44,fill='#155366',cornerRadius=10)
 node('text','Back label',back,16,12,240,24,'Back to sessions',fontFamily='Inter',fontSize=15,fill='#ffffff')
 cmd('proto.interaction.add',{'id':instance,'dest':details});cmd('proto.interaction.add',{'id':back,'dest':home});cmd('proto.flow.add',{'start':home,'name':'Workshop booking'})
 cmd('style.create',{'type':'paint','name':'Club/Primary','from':button})
 collection=cmd('variable.createCollection',{'name':'Club theme','modes':['Light','Dark']})
 r['collection']=collection
 # A number variable tests binding without changing the readable visual palette.
 variable=cmd('variable.create',{'collection':collection['id'],'name':'Button radius','type':'number','value':10})
 r['variable']=variable
 cmd('variable.bind',{'ids':[button],'field':'cornerRadius','variable':variable['id']})
 tool('undo');tool('redo')
 tool('save_file',{'path':str(base/'repair-club.figcraft')})
 r['document']=tool('inspect_document',{'depth':8});assert 'THE REPAIR CLUB' in json.dumps(r['document'])
 r['ids']={'home':home,'details':details,'heading':title,'button':button,'instance':instance,'back':back,'stack':stack}
 (base/'ids.json').write_text(json.dumps(r['ids']))
 # The native document is the durable working copy. Hide the off-screen component for export.
 tool('set_properties',{'ids':[button],'props':{'visible':False}})
 tool('save_file',{'path':str(base/'export-source.figcraft')})
 for ext in ['svg','pdf','png','webp','jpg','json','fig']:
  out=subprocess.run([cli,'convert',str(base/'export-source.figcraft'),str(base/('screens.'+ext))],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=90)
  assert out.returncode==0,(ext,out.stderr);assert (base/('screens.'+ext)).stat().st_size>40
  r['export_'+ext]={'bytes':(base/('screens.'+ext)).stat().st_size,'notes':out.stderr.strip()[:1800]}
 tool('open_file',{'path':str(base/'repair-club.figcraft')});reopened=tool('inspect_document',{'depth':8});assert 'THE REPAIR CLUB' in json.dumps(reopened)
 for ext in ['svg','fig']:
  out=subprocess.run([cli,'convert',str(base/('screens.'+ext)),str(base/('roundtrip-'+ext+'.figcraft'))],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=90);assert out.returncode==0,out.stderr
  tool('open_file',{'path':str(base/('roundtrip-'+ext+'.figcraft'))}); inspected=tool('inspect_document',{'depth':8})
  if ext=='fig':assert 'THE REPAIR CLUB' in json.dumps(inspected),'FIG round trip lost text'
  else:
   info=json.loads(subprocess.check_output([cli,'info',str(base/'roundtrip-svg.figcraft'),'--json'],env=env).decode());assert info['nodes']>10
   r['svg_roundtrip_nodes']=info['nodes']
 for toolname,args in [('open_file',{'path':'/etc/hostname'}),('save_file',{'path':'/tmp/outside-figcraft-root.figcraft'})]:
  assert rpc('tools/call',{'name':toolname,'arguments':args}).get('isError')
 text=subprocess.check_output(['pdftotext',str(base/'screens.pdf'),'-']).decode();assert 'THE REPAIR CLUB' in text and 'MAKE AND MEND' in text
 r['checks']=['no-display MCP','two original interface screens','auto layout','reusable component/instance','paint style','variable binding','prototype flow/navigation links','undo/redo','native reopen','SVG vector round trip and FIG text round trip','SVG/PDF/PNG/JPG/WebP/JSON/FIG export','independent PDF text','read/write confinement'];r['passed']=True
except Exception as e:r.update(passed=False,error=repr(e))
finally:
 if p:
  p.stdin.close()
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=10)
(base/'headless-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['document','initialize']},indent=2));raise SystemExit(0 if r.get('passed') else 1)
