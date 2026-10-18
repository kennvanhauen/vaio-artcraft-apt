#!/usr/bin/env python3
"""Create the pinned launcher build tree; retain upstream checkout unmodified."""
from pathlib import Path
import io
import shutil
import subprocess
import tarfile

root = Path(__file__).resolve().parents[1]
upstream = root / 'upstream/craft-launcher'
revision = '9cef5d2a0f207da50d31547a726057ea40f7e5b4'
actual = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
if actual != revision:
    raise SystemExit('Unexpected launcher revision: '+actual)
destination = root / '.build/launcher-port'
if destination.exists():
    raise SystemExit('Build tree exists; inspect/reuse or move it aside explicitly')
destination.mkdir(parents=True)
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git', '-C', str(upstream), 'archive', revision]))) as archive:
    archive.extractall(destination, filter='data')
subprocess.run(['patch', '-p1', '-i', str(root / 'ports/launcher-xenial.patch')], cwd=destination, check=True)
shutil.copytree(root / 'ports/launcher-vaio', destination / 'apps/artcraft-launcher-vaio')
shutil.copy2(root / 'ports/launcher-vaio/launcher.svg', destination / 'assets/vaio-launcher.svg')
# The new workspace member adds dependency edges. Retain its checked lockfile.
lock = root / 'ports/launcher-vaio.Cargo.lock'
if lock.exists():
    shutil.copy2(lock, destination / 'Cargo.lock')
print(destination)
