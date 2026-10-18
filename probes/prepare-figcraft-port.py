#!/usr/bin/env python3
"""Recreate the pinned downstream FigCraft tree without changing upstream."""
from pathlib import Path
import io, subprocess, tarfile
root = Path(__file__).resolve().parents[1]
revision = 'a0d1162976fac1e4a8b8fd49a3948e9d6bad6f40'
source = root/'upstream/figcraft'
target = root/'.build/figcraft-port'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip() == revision
if target.exists():
    raise SystemExit('Build tree already exists; inspect it before reusing')
target.mkdir()
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','-C',str(source),'archive',revision]))) as archive:
    archive.extractall(target, filter='data')
subprocess.run(['patch','-p1','-i',str(root/'ports/figcraft-xenial.patch')],cwd=target,check=True)
(target/'Cargo.lock').write_bytes((root/'ports/figcraft-vaio.Cargo.lock').read_bytes())
print(target)
