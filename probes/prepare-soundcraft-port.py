#!/usr/bin/env python3
"""Recreate the pinned SoundCraft port without replacing an existing work tree."""
import io
import os
from pathlib import Path
import subprocess
import tarfile

root = Path(__file__).resolve().parents[1]
revision = 'e85a4801e9029c9a1f5ce536b11be65aea832ed8'
source, target = root/'upstream/soundcraft', root/'.build/soundcraft-port'
assert subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == revision
if target.exists():
    raise SystemExit('Build tree exists; inspect it before reusing')
target.mkdir()
data = subprocess.check_output(['git', '-C', str(source), 'archive', revision])
with tarfile.open(fileobj=io.BytesIO(data)) as archive:
    archive.extractall(target, filter='data')
env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(target.parent.resolve()))
for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
    env.pop(name, None)
subprocess.run(['git', 'apply', str(root/'ports/soundcraft-xenial.patch')], cwd=target, env=env, check=True)
assert (target/'Cargo.lock').read_bytes() == (root/'ports/soundcraft-vaio.Cargo.lock').read_bytes()
print(target)
