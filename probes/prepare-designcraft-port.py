#!/usr/bin/env python3
"""Recreate the pinned downstream DesignCraft tree without changing upstream."""
from pathlib import Path
import io, subprocess, tarfile
root = Path(__file__).resolve().parents[1]
revision = 'ecd7e5d063eb12fa5e61fe61c9b8a77bb3c9110a'
source = root/'upstream/designcraft'
target = root/'.build/designcraft-port'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip() == revision
if target.exists():
    raise SystemExit('Build tree already exists; inspect it before reusing')
target.mkdir()
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','-C',str(source),'archive',revision]))) as archive:
    archive.extractall(target, filter='data')
subprocess.run(['patch','-p1','-i',str(root/'ports/designcraft-xenial.patch')],cwd=target,check=True)
(target/'Cargo.lock').write_bytes((root/'ports/designcraft-vaio.Cargo.lock').read_bytes())
print(target)
