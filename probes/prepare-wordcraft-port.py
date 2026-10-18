#!/usr/bin/env python3
"""Create a disposable build tree from the audited, pinned WordCraft checkout."""
from pathlib import Path
import io
import subprocess
import tarfile

root = Path(__file__).resolve().parents[1]
upstream = root / 'upstream/wordcraft'
revision = 'd6f20f93fd22deb441b2216ecfd65acb15ea8b64'
actual = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
if actual != revision:
    raise SystemExit('Upstream revision changed: ' + actual)
destination = root / '.build/wordcraft-port'
if destination.exists():
    raise SystemExit('Build tree already exists; reuse it or explicitly move it aside')
destination.mkdir(parents=True)
data = subprocess.check_output(['git', '-C', str(upstream), 'archive', revision])
with tarfile.open(fileobj=io.BytesIO(data)) as archive:
    archive.extractall(destination, filter='data')
subprocess.run(['patch', '-p1', '-i', str(root / 'ports/wordcraft-xenial.patch')],
               cwd=destination, check=True)
print(destination)
