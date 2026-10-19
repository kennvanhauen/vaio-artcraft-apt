#!/usr/bin/env python3
"""Three original slides: formats, GUI edit, slideshow, quiet idle; audio off."""
import json,os,re,socket,struct,subprocess,time,zipfile,zlib
from pathlib import Path
base=Path('/tmp/vaio-deckcraft-test');base.mkdir(parents=True,exist_ok=True)
binary=os.environ.get('VAIO_DECK_BINARY','/tmp/vaio-deckcraft-test/deckcraft')
cli=os.environ.get('VAIO_DECK_CLI','/tmp/vaio-deckcraft-test/deckcraft-cli')
env=dict(os.environ,DISPLAY=':0',DECKCRAFT_NO_AUDIO='1',DECKCRAFT_NO_PREFS='1',DECKCRAFT_NO_RECOVERY='1',
         XDG_CONFIG_HOME=str(base/'config'),XDG_DATA_HOME=str(base/'data'),LD_LIBRARY_PATH='/usr/lib/wordcraft-vaio/lib')
result={'checks':[],'timings':[]};process=None;connection=None
def run(*args):
    at=time.monotonic();p=subprocess.run([cli]+list(args),env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=50)
    result['timings'].append({'action':args[0],'seconds':round(time.monotonic()-at,3)})
    if p.returncode:raise RuntimeError(args[0]+': '+p.stderr[:800])
    return p.stdout
def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',160,70,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+bytes([40,110,180])*160 for _ in range(70))))+chunk(b'IEND',b'')
(base/'original-blue.png').write_bytes(png)
try:
    subprocess.run(['xscreensaver-command','-deactivate'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    commands=[('slide.new',{'layout':'titleAndContent','title':'VAIO synthetic presentation','body':'A short original presentation. No personal information.\ncafé; Ελληνικά; 日本語'}),
              ('slide.new',{'layout':'titleAndContent','title':'Simple project','body':'Prepare a draft\nReview the figures\nShare the finished presentation'}),
              ('slide.new',{'layout':'blank'}),('slide.delete',{'index':0}),('slide.go',{'index':2}),
              ('shape.insert',{'preset':'roundRect','rect':[40,40,350,70],'text':'Original shapes and chart'}),
              ('insert.picture',{'path':str(base/'original-blue.png'),'rect':[40,160,200,90]}),
              ('insert.chart',{'type':'column','rect':[300,145,550,300],'categories':['Alpha','Beta','Gamma'],'series':[{'name':'Synthetic values','values':[2,5,3]}]}),
              ('slide.notes',{'text':'Original presenter notes for the test.'}),
              ('transition.set',{'index':1,'kind':'fade','duration':300})]
    args=['run']
    for name,params in commands:args+=['--cmd',name+'='+json.dumps(params)]
    args+=['--save',str(base/'original.deckcraft')];run(*args)
    result['initial_info']=json.loads(run('info',str(base/'original.deckcraft')))
    assert len(result['initial_info']['slides'])==3
    for ext in ['pptx','pdf','md']:
        run('convert',str(base/'original.deckcraft'),str(base/('original.'+ext)))
        assert (base/('original.'+ext)).stat().st_size>100
    with zipfile.ZipFile(str(base/'original.pptx')) as z:
        names=z.namelist();assert len([n for n in names if re.match(r'ppt/slides/slide\d+\.xml$',n)])==3
        assert any(n.startswith('ppt/charts/chart') for n in names)
        assert any(n.startswith('ppt/media/') for n in names)
        assert any(n.startswith('ppt/notesSlides/notesSlide') for n in names)
    run('convert',str(base/'original.pptx'),str(base/'roundtrip.deckcraft'))
    assert len(json.loads(run('info',str(base/'roundtrip.deckcraft')))['slides'])==3
    run('render',str(base/'original.pptx'),'--slide','0','--scale','1',str(base/'slide.png'))
    result['checks']+=['three-slide creation','shapes/picture/chart/notes','PPTX save/reopen','PDF and outline export','slide rendering']
    def screensaver_awake():
        return 'screen non-blanked' in subprocess.check_output(['xscreensaver-command','-time'],env=env).decode()
    def wait_screensaver(awake):
        until=time.monotonic()+10
        while time.monotonic()<until:
            state=screensaver_awake()
            if state==awake:return state
            time.sleep(.2)
        return state
    def activate_screensaver():
        # Show teardown can still be completing a wake command. Prove the actual
        # blanked state, retrying that short command race rather than trusting rc.
        for attempt in range(3):
            command=subprocess.run(['xscreensaver-command','-activate'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            result.setdefault('screensaver_activation_returncodes',[]).append(command.returncode)
            if wait_screensaver(False)==False:return
            time.sleep(.3)
        raise AssertionError('Test screensaver activation failed')
    result['screensaver_before_awake']=wait_screensaver(True)
    log=(base/'application.log').open('w')
    process=subprocess.Popen([binary,'--control','7991',str(base/'original.pptx')],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
    until=time.monotonic()+35
    while time.monotonic()<until:
        if process.poll() is not None:raise RuntimeError('GUI exited at startup')
        try:connection=socket.create_connection(('127.0.0.1',7991),timeout=35);break
        except OSError:time.sleep(.2)
    assert connection,'Control endpoint unavailable'
    channel=connection.makefile('rwb',buffering=0);serial=0
    def request(method,params=None):
        global serial
        serial+=1;at=time.monotonic();channel.write((json.dumps({'id':serial,'method':method,'params':params or {}})+'\n').encode())
        reply=json.loads(channel.readline().decode());result['timings'].append({'action':method,'seconds':round(time.monotonic()-at,3)})
        if not reply.get('ok'):raise RuntimeError(method+': '+str(reply.get('error')))
        return reply.get('result')
    def execute(command,params=None):return request('engine.execute',{'command':command,'params':params or {}})
    time.sleep(1);request('ui.resize',{'width':1100,'height':650})
    execute('slide.go',{'index':0})
    created=execute('insert.textBox',{'rect':[70,380,700,70],'text':''})
    result['created_text_box']=created
    # Enter the selected text box through the same engine path as double-click editing.
    execute('text.edit',{'id':created['id']})
    request('ui.text',{'text':'Edited through the VAIO GUI.'});request('ui.inspect')
    request('ui.screenshot',{'path':str(base/'editing-ui.png')})
    def sample():
        f=Path('/proc/%d/stat'%process.pid).read_text().rsplit(')',1)[1].split()
        rss=next(int(l.split()[1]) for l in Path('/proc/%d/status'%process.pid).read_text().splitlines() if l.startswith('VmRSS:'))
        return int(f[11])+int(f[12]),rss
    time.sleep(2);before,rss=sample();at=time.monotonic();time.sleep(5);after,rss=sample()
    result['editing_idle_cpu_percent_one_logical_cpu']=round(100*(after-before)/os.sysconf('SC_CLK_TCK')/(time.monotonic()-at),2)
    result['rss_kib']=rss
    request('ui.key',{'key':'Escape'});request('ui.inspect')
    request('app.save',{'path':str(base/'edited.pptx')})
    assert 'Edited through the VAIO GUI.' in run('info',str(base/'edited.pptx')) or 'Edited through the VAIO GUI.' in run('run','--in',str(base/'edited.pptx'),'--cmd','slide.inspect={"index":0}','--print')
    activate_screensaver()
    request('show.start',{'from':0});time.sleep(1)
    result['screensaver_awake_during_show']=wait_screensaver(True)
    assert result['screensaver_awake_during_show'],'Presentation did not wake XScreenSaver'
    result['show_initial']=request('ui.inspect')
    assert result['show_initial']['showing']['slide']==0 and result['show_initial']['window']==[1600.0,768.0],'Slide show did not start full screen'
    time.sleep(3);before,rss=sample();at=time.monotonic();time.sleep(5);after,rss=sample()
    result['static_show_cpu_percent_one_logical_cpu']=round(100*(after-before)/os.sysconf('SC_CLK_TCK')/(time.monotonic()-at),2)
    if os.environ.get('VAIO_DECK_KEEPALIVE_CHECK')=='1':
        activate_screensaver();time.sleep(46)
        result['screensaver_periodic_keepalive']=wait_screensaver(True)
        assert result['screensaver_periodic_keepalive'],'Periodic presentation keepalive failed'
    request('ui.key',{'key':'Right'});time.sleep(1)
    result['show_next']=request('ui.inspect')
    assert result['show_next']['showing']['slide']==1,'Next slide did not advance'
    request('ui.screenshot',{'path':str(base/'slideshow-ui.png')})
    request('show.end');time.sleep(1.2)
    activate_screensaver()
    result['screensaver_still_works_after_show']=True
    subprocess.check_call(['xscreensaver-command','-deactivate'],env=env,stdout=subprocess.DEVNULL)
    execute('transition.timing',{'index':0,'after':1000})
    execute('show.setup',{'useTimings':True,'loop':False})
    request('show.start',{'from':0});time.sleep(2.2)
    result['timed_show']=request('ui.inspect')
    assert result['timed_show']['showing']['slide']==1,'Timed advance did not run'
    request('show.end');time.sleep(.3)
    request('app.open',{'path':str(base/'edited.pptx')})
    request('ui.screenshot',{'path':str(base/'deckcraft-ui.png')})
    time.sleep(2);before,rss=sample();at=time.monotonic();time.sleep(5);after,rss=sample()
    result['settled_idle_cpu_percent_one_logical_cpu']=round(100*(after-before)/os.sysconf('SC_CLK_TCK')/(time.monotonic()-at),2)
    result['loaded_private_xcb']=sorted(set(l.split()[-1] for l in Path('/proc/%d/maps'%process.pid).read_text().splitlines() if '/lib/libxcb.so.1' in l))
    request('app.quit');process.wait(timeout=15)
    result['checks']+=['GUI typing','edited PPTX save','full-screen slideshow','next slide/fade','return to editor','automatic timed advance','scoped XScreenSaver keepalive']
    result['passed']=True
except Exception as error:result.update(passed=False,error=str(error))
finally:
    subprocess.run(['xscreensaver-command','-deactivate'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if process and process.poll() is None:process.terminate();process.wait(timeout=10)
    if connection:connection.close()
(base/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['show_initial','show_next','timed_show']},indent=2));raise SystemExit(0 if result.get('passed') else 1)
