#!/usr/bin/env python3
"""Recreate the pinned downstream CADCraft tree without changing upstream."""
from pathlib import Path
import io, subprocess, tarfile
root = Path(__file__).resolve().parents[1]
revision = '0cc66ad3066e71f2c3d4cacb7de905e79ba1c95b'
source = root/'upstream/cadcraft'
target = root/'.build/cadcraft-port'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip() == revision
if target.exists():
    raise SystemExit('Build tree already exists; inspect it before reusing')
target.mkdir()
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','-C',str(source),'archive',revision]))) as archive:
    archive.extractall(target, filter='data')
subprocess.run(['patch','-p1','-i',str(root/'ports/cadcraft-xenial.patch')],cwd=target,check=True)
(target/'Cargo.lock').write_bytes((root/'ports/cadcraft-vaio.Cargo.lock').read_bytes())
print(target)
