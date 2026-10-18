#!/usr/bin/env python3
"""Repeat CADCraft acceptance checks through the actual installed wrappers."""
import json,os,shutil,subprocess
from pathlib import Path
base=Path('/tmp/vaio-cadcraft-test')
env=dict(os.environ,VAIO_CAD_BINARY='/usr/bin/cadcraft-vaio',VAIO_CAD_CLI='/usr/bin/cadcraft-vaio-cli')
steps=[('headless','cadcraft_headless.py',base/'headless-result.json'),('gui','cadcraft_gui.py',base/'gui-result.json'),('native-dialogs','cadcraft_native_dialogs.py',base/'native-dialogs/result.json'),('proof','cadcraft_installed_proof.py',base/'installed-proof.json')]
r={'steps':[]}
for name,script,result in steps:
 with (base/('installed-'+name+'.log')).open('w') as log:
  subprocess.run(['python3',str(base/script)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
 data=json.loads(result.read_text());assert data['passed'],data
 if name=='gui':assert data['private_xcb']==['/usr/lib/cadcraft-vaio/lib/libxcb.so.1'],data['private_xcb']
 shutil.copy2(str(result),str(base/('installed-'+name+'-result.json')))
 r['steps'].append(name)
 print('PASS: installed '+name,flush=True)
r['passed']=True;(base/'installed-checks-result.json').write_text(json.dumps(r,indent=2)+'\n')
