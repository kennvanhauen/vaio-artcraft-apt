#!/usr/bin/env python3
"""Recreate the pinned downstream VectorCraft tree without changing upstream."""
from pathlib import Path
import io, subprocess, tarfile
root = Path(__file__).resolve().parents[1]
revision = 'a466625c8987550635cda951ebf36e08e1e80a56'
source = root/'upstream/vectorcraft'
target = root/'.build/vectorcraft-port'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip() == revision
if target.exists():
    raise SystemExit('Build tree already exists; inspect it before reusing')
target.mkdir()
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','-C',str(source),'archive',revision]))) as archive:
    archive.extractall(target, filter='data')
subprocess.run(['patch','-p1','-i',str(root/'ports/vectorcraft-xenial.patch')],cwd=target,check=True)
(target/'Cargo.lock').write_bytes((root/'ports/vectorcraft-vaio.Cargo.lock').read_bytes())
print(target)
