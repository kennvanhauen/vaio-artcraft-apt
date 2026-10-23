#!/usr/bin/python3
"""Click all nine real Open actions in a disposable launcher/profile.

Only children spawned by this launcher are closed. A search avoids relying on
card order, and the full grid is captured before/after. No recording is armed.
"""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time

parent=Path(os.environ.get('VAIO_LAUNCHER_TEST_PARENT','/tmp'))
base=Path(tempfile.mkdtemp(prefix='vaio-launcher-nine-',dir=str(parent)))
binary=os.environ.get('VAIO_LAUNCHER_BINARY','/usr/bin/vaio-app-launcher')
folder=Path(json.loads((Path.home()/'.local/share/vaio-artcraft-defaults/settings.json').read_text())['documents_folder'])
env=dict(os.environ,DISPLAY=':0',XDG_CONFIG_HOME=str(base/'config'),XDG_DATA_HOME=str(base/'data'),XDG_CACHE_HOME=str(base/'cache'),
         CADCRAFT_CONFIG_DIR=str(base/'cad-profile'),WORDCRAFT_PROFILE_DIR=str(base/'word-profile'),WORDCRAFT_NO_PREFS='1',
         GRIDCRAFT_NO_PREFS='1',DECKCRAFT_NO_PREFS='1',DECKCRAFT_NO_RECOVERY='1',DECKCRAFT_NO_AUDIO='1',VECTORCRAFT_NO_PREFS='1',
         DESIGNCRAFT_NO_PREFS='1',DESIGNCRAFT_CONFIG_DIR=str(base/'design-profile'),FIGCRAFT_CONFIG_DIR=str(base/'fig-profile'),
         FIGCRAFT_NO_PREFS='1',SOUNDCRAFT_CONFIG_DIR=str(base/'sound-profile'),PDFCRAFT_SYSTEM_FONTS='0',VAIO_ARTCRAFT_DOCUMENTS=str(folder))
env['PATH']=str(Path.home()/'.local/share/vaio-artcraft-defaults/bin')+':'+env.get('PATH','/usr/bin:/bin')
subprocess.call(['xscreensaver-command','-deactivate'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
log=(base/'application.log').open('w');process=None;children=[]
result={'passed':False,'opened':[],'fixture':str(base),'recording_armed':False}


def command(*args):
    return subprocess.check_output(list(args),env=env).decode()


def click(x,y):
    command('xdotool','windowactivate','--sync',window,'mousemove','--window',window,str(x),str(y),'click','1')
    time.sleep(.5)


def search(text):
    click(1300,82);command('xdotool','key','--clearmodifiers','ctrl+a')
    if text:command('xdotool','type','--clearmodifiers','--delay','5',text)
    else:command('xdotool','key','BackSpace')
    time.sleep(.8)


try:
    snapshot=json.loads(subprocess.check_output([binary,'--check'],env=env).decode())
    result['snapshot']=snapshot
    applications=snapshot['applications'];assert len(applications)==9,applications
    sound=next(x for x in applications if x['package']=='soundcraft-vaio');assert sound['installed']=='0.12.1~vaio2',sound
    process=subprocess.Popen([binary],env=env,cwd=str(folder),stdout=log,stderr=log)
    time.sleep(12)
    window=command('xdotool','search','--onlyvisible','--pid',str(process.pid)).splitlines()[-1]
    command('xdotool','windowactivate','--sync',window)
    subprocess.check_call(['import','-window',window,str(base/'all-nine.png')],env=env)
    for app in ['cadcraft','deckcraft','designcraft','figcraft','gridcraft','pdfcraft','soundcraft','vectorcraft','wordcraft']:
        search(app);click(200,330)
        until=time.monotonic()+12;found=None
        while time.monotonic()<until:
            ids=Path('/proc/%d/task/%d/children'%(process.pid,process.pid)).read_text().split()
            for value in ids:
                pid=int(value)
                try:
                    executable=Path('/proc/%d/cmdline'%pid).read_bytes().split(b'\0')[0]
                    profile=Path('/proc/%d/environ'%pid).read_bytes().split(b'\0')
                    if executable==('/usr/lib/'+app+'-vaio/bin/'+app).encode() and ('XDG_DATA_HOME='+str(base/'data')).encode() in profile:
                        found=pid;break
                except OSError:pass
            if found:break
            time.sleep(.2)
        assert found,'Open did not launch '+app
        children.append(found);time.sleep(2)
        assert Path('/proc/%d'%found).exists(),app+' exited at startup'
        profile=Path('/proc/%d/environ'%found).read_bytes().split(b'\0')
        assert ('VAIO_ARTCRAFT_DOCUMENTS='+str(folder)).encode() in profile
        assert Path('/proc/%d/cwd'%found).resolve()==folder
        result['opened'].append({'app':app,'document_default_inherited':True})
        os.kill(found,signal.SIGTERM)
        until=time.monotonic()+5
        while time.monotonic()<until and Path('/proc/%d'%found).exists():time.sleep(.1)
        assert not Path('/proc/%d'%found).exists(),'Child was not reaped: '+app
    search('');command('xdotool','mousemove','--window',window,'700','45');time.sleep(8)
    subprocess.check_call(['import','-window',window,str(base/'final-nine.png')],env=env)
    def sample():
        fields=Path('/proc/%d/stat'%process.pid).read_text().rsplit(')',1)[1].split()
        rss=int(re.search(r'^VmRSS:\s+(\d+) kB',Path('/proc/%d/status'%process.pid).read_text(),re.M).group(1))
        return int(fields[11])+int(fields[12]),rss
    a,_=sample();start=time.monotonic();time.sleep(8);b,rss=sample()
    result.update(idle_cpu_percent_one_logical_cpu=100*(b-a)/os.sysconf('SC_CLK_TCK')/(time.monotonic()-start),rss_kib=rss,passed=True)
except BaseException as error:
    import traceback
    result.update(error=repr(error),traceback=traceback.format_exc())
finally:
    for child in children:
        try:
            if re.search(r'^PPid:\s+%d$'%process.pid,Path('/proc/%d/status'%child).read_text(),re.M):os.kill(child,signal.SIGTERM)
        except OSError:pass
    if process and process.poll() is None:process.terminate();process.wait(timeout=10)
    log.close();(base/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    (parent/'launcher-nine-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
