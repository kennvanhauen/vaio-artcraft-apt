#!/usr/bin/env python3
"""Extract the pinned optional native font input, then verify its manifest/notices."""
from pathlib import Path
import io, subprocess, tarfile
root = Path(__file__).resolve().parents[1]
source = root/'upstream/craft-fonts'
revision = '43913056ce82a3fdad0ef69f6b88d1dc922a8104'
target = root/'.build/figcraft-fonts'
if not source.exists():
    subprocess.run(['git','clone','--no-checkout','https://github.com/storytold/craft-fonts',str(source)],check=True)
subprocess.run(['git','-C',str(source),'fetch','origin',revision],check=True)
if target.exists():
    raise SystemExit('Font tree already exists; run verify-figcraft-fonts.py before reuse')
target.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','-C',str(source),'archive',revision]))) as archive:
    archive.extractall(target,filter='data')
subprocess.run(['python3',str(root/'probes/verify-figcraft-fonts.py')],check=True)
