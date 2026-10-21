#!/usr/bin/env python3
"""Check real GUI startup tightens a disposable pre-existing recovery folder."""
import json,os,subprocess,time
from pathlib import Path
base=Path('/tmp/vaio-everyday/pdfcraft-recovery-permissions');base.mkdir(parents=True,exist_ok=True)
recovery=base/'data/pdfcraft/recovery';recovery.mkdir(parents=True,exist_ok=True);recovery.chmod(0o755)
runtime=base/'runtime';runtime.mkdir(exist_ok=True,mode=0o700)
binary=os.environ.get('VAIO_PDF_BINARY','/usr/bin/pdfcraft-vaio')
cli=os.environ.get('VAIO_PDF_CLI','/usr/bin/pdfcraft-vaio-cli')
env=dict(os.environ,DISPLAY=':0',PDFCRAFT_RENDERER='gl',PDFCRAFT_SYSTEM_FONTS='0',XDG_DATA_HOME=str(base/'data'),XDG_CONFIG_HOME=str(base/'config'),XDG_CACHE_HOME=str(base/'cache'),XDG_RUNTIME_DIR=str(runtime))
control=base/'control.json';result={'passed':False};process=None
try:
    assert not control.exists(),'Use a fresh private test directory'
    with (base/'app.log').open('w') as log:
        process=subprocess.Popen([binary,'--control',str(control)],env=env,stdout=log,stderr=log)
        until=time.monotonic()+35
        while time.monotonic()<until:
            if process.poll() is not None:raise RuntimeError('GUI exited at startup')
            if control.exists() and recovery.stat().st_mode & 0o777 == 0o700:break
            time.sleep(.2)
        assert recovery.stat().st_mode & 0o777 == 0o700,'Existing recovery folder was not tightened'
        assert control.stat().st_mode & 0o077 == 0,'Control file permissions too broad'
        subprocess.check_output([cli,'ui','--control',str(control),'quit'],env=env,stderr=subprocess.STDOUT,timeout=30)
        process.wait(timeout=15)
    result.update(passed=True,recovery_mode='0700',checks=['existing 0755 recovery directory tightened to 0700 by actual Xenial GUI','control metadata owner-only','clean GUI quit'])
except Exception as error:result['error']=str(error)
finally:
    if process is not None and process.poll() is None:process.terminate();process.wait(timeout=10)
(base/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
