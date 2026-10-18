#!/usr/bin/env python3
"""Stage matching Xenial ALSA development data on the build host only."""
import hashlib,io,tarfile,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
name='libasound2-dev_1.1.0-0ubuntu1_i386.deb'
digest='1fe947aeea397b801eb1ef912906ed1e0e9d0cc727fcf50402b011a89eb6ca5e'
path=root/'.build'/name
if not path.exists():
    urllib.request.urlretrieve('https://archive.ubuntu.com/ubuntu/pool/main/a/alsa-lib/'+name,path)
data=path.read_bytes()
if hashlib.sha256(data).hexdigest()!=digest:raise SystemExit('ALSA input hash mismatch')
offset=8
assert data[:8]==b'!<arch>\n'
while offset+60<=len(data):
    header=data[offset:offset+60];size=int(header[48:58])
    if header[:16].decode().strip().rstrip('/').startswith('data.tar'):
        with tarfile.open(fileobj=io.BytesIO(data[offset+60:offset+60+size])) as archive:
            archive.extractall(root/'.build/sysroot',filter='data')
    offset+=60+size+size%2
lib=root/'.build/sysroot/usr/lib/i386-linux-gnu'
if not (lib/'libasound.so.2.0.0').is_file():
    raise SystemExit('Copy the target VAIO runtime libasound.so.2.0.0 into the sysroot; do not install headers on the VAIO.')
for name in ['libasound.so','libasound.so.2']:
    path=lib/name
    if path.is_symlink():path.unlink()
    if not path.exists():path.symlink_to('libasound.so.2.0.0')
print('Verified ALSA 1.1.0 headers staged in the build-host sysroot')
