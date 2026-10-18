#!/usr/bin/env python3
"""Exercise the exact helper's parsing/transaction flow with harmless mock commands."""
import json,os,subprocess,tempfile
from pathlib import Path
source=(Path(__file__).resolve().parents[1]/'ports/launcher-vaio/apt-action').read_text()
with tempfile.TemporaryDirectory(prefix='vaio-apt-helper-') as directory:
    root=Path(directory);log=root/'calls';helper=root/'helper'
    # Only the test copy's command lookup changes. No real APT or root command runs.
    helper.write_text(source.replace('PATH=/usr/sbin:/usr/bin:/sbin:/bin','PATH='+directory,1))
    (root/'id').write_text('#!/bin/sh\nprintf "%s\\n" "${TEST_UID:-0}"\n')
    (root/'apt-get').write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$TEST_LOG"
case "$*" in *update) exit "${TEST_UPDATE_STATUS:-0}";; esac
exit 0
''')
    for name in ['id','apt-get']:(root/name).chmod(0o755)
    def run(args,**extra):
        log.write_text('')
        p=subprocess.run(['/bin/sh',str(helper)]+args,input='\n',text=True,capture_output=True,
                         env=dict(os.environ,TEST_LOG=str(log),**extra))
        return p.returncode,log.read_text().splitlines()
    invalid=[[],['install'],['upgrade','wordcraft-vaio'],['install','bash'],
             ['install','--allow-unauthenticated'],['install','wordcraft-vaio; true'],
             ['remove','wordcraft-vaio','gridcraft-vaio','pdfcraft-vaio','deckcraft-vaio','vectorcraft-vaio','designcraft-vaio','figcraft-vaio','wordcraft-vaio']]
    for args in invalid:
        status,calls=run(args);assert status!=0 and calls==[],(args,status,calls)
    status,calls=run(['install','wordcraft-vaio'],TEST_UID='1000');assert status!=0 and calls==[]
    status,calls=run(['install','wordcraft-vaio','gridcraft-vaio','pdfcraft-vaio'])
    assert status==0 and len(calls)==2 and calls[-1]=='--no-remove --no-install-recommends install wordcraft-vaio gridcraft-vaio pdfcraft-vaio',calls
    status,calls=run(['install','wordcraft-vaio','gridcraft-vaio','pdfcraft-vaio','deckcraft-vaio'])
    assert status==0 and len(calls)==2 and calls[-1].endswith('install wordcraft-vaio gridcraft-vaio pdfcraft-vaio deckcraft-vaio'),calls
    status,calls=run(['install','wordcraft-vaio','gridcraft-vaio','pdfcraft-vaio','deckcraft-vaio','vectorcraft-vaio'])
    assert status==0 and len(calls)==2 and calls[-1].endswith('install wordcraft-vaio gridcraft-vaio pdfcraft-vaio deckcraft-vaio vectorcraft-vaio'),calls
    status,calls=run(['install','wordcraft-vaio','gridcraft-vaio','pdfcraft-vaio','deckcraft-vaio','vectorcraft-vaio','designcraft-vaio'])
    assert status==0 and len(calls)==2 and calls[-1].endswith('vectorcraft-vaio designcraft-vaio'),calls
    status,calls=run(['install','wordcraft-vaio','gridcraft-vaio','pdfcraft-vaio','deckcraft-vaio','vectorcraft-vaio','designcraft-vaio','figcraft-vaio'])
    assert status==0 and len(calls)==2 and calls[-1].endswith('designcraft-vaio figcraft-vaio'),calls
    status,calls=run(['remove','gridcraft-vaio','pdfcraft-vaio'])
    assert status==0 and calls==['remove gridcraft-vaio pdfcraft-vaio'],calls
    status,calls=run(['install','pdfcraft-vaio'],TEST_UPDATE_STATUS='42')
    assert status==42 and len(calls)==1,(status,calls)
print(json.dumps({'passed':True,'invalid_cases':len(invalid),'checks':['root required','exact allowlist','single batch install','batch removal','update failure prevents install']}))
