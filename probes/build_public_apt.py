#!/usr/bin/env python3
"""Stage public APT metadata and packages compatible with Xenial APT 1.2.

The signing home is local, ignored, mode 0700 and never copied to the output.
No signing credential is uploaded to GitHub. Re-run for each package release.
"""
import argparse
from datetime import datetime, timezone
from email.utils import format_datetime
import gzip
import hashlib
import io
from pathlib import Path
import subprocess
import tarfile
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('package', type=Path)
parser.add_argument('--tag', required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
key_home = root / '.build/apt-signing'
if key_home.stat().st_mode & 0o077:
    raise SystemExit('Signing directory must be private (0700)')
content = args.package.read_bytes()
if not content.startswith(b'!<arch>\n'):
    raise SystemExit('Not a Debian ar archive')
position = 8
control = None
while position + 60 <= len(content):
    header = content[position:position+60]
    size = int(header[48:58])
    if header[:16].decode().strip().rstrip('/') == 'control.tar.gz':
        with tarfile.open(fileobj=io.BytesIO(content[position+60:position+60+size])) as ar:
            control = ar.extractfile('./control').read().decode()
        break
    position += 60 + size + size % 2
if not control or '\nArchitecture: i386\n' not in '\n'+control:
    raise SystemExit('Missing i386 control metadata')
repo = args.output.resolve()
binary = repo / 'dists/xenial/main/binary-i386'
binary.mkdir(parents=True, exist_ok=True)
url = 'pool/main/'+args.package.name
(repo/'pool/main').mkdir(parents=True, exist_ok=True)
shutil.copy2(args.package, repo/url)
index = (control.rstrip()+'\nFilename: '+url+'\nSize: '+str(len(content))
         +'\nMD5sum: '+hashlib.md5(content).hexdigest()
         +'\nSHA256: '+hashlib.sha256(content).hexdigest()+'\n\n')
# Preserve other package names when publishing another application.
previous = binary / 'Packages'
package_name = next(line for line in control.splitlines() if line.startswith('Package: '))
if previous.exists():
    records = [record for record in previous.read_text().strip().split('\n\n')
               if record and not record.startswith(package_name+'\n')]
    index = ''.join(record+'\n\n' for record in records)+index
(binary / 'Packages').write_text(index)
(binary / 'Packages.gz').write_bytes(gzip.compress(index.encode(), mtime=0))
(binary / 'Release').write_text('Archive: xenial\nComponent: main\nArchitecture: i386\n')
suite = repo / 'dists/xenial'
# A static archive remains usable between releases. Key expiration still applies.
# No short Valid-Until: this repository does not require daily automated signing.
release = ('Origin: VAIO ArtCraft\nLabel: VAIO ArtCraft previews\n'
           'Suite: xenial\nCodename: xenial\nArchitectures: i386\nComponents: main\n'
           'Description: Unofficial ArtCraft previews for Ubuntu Xenial i386\n'
           'Date: '+format_datetime(datetime.now(timezone.utc), usegmt=True)+'\n')
for label, algorithm in (('MD5Sum', hashlib.md5), ('SHA256', hashlib.sha256)):
    release += label+':\n'
    for name in ('Packages', 'Packages.gz', 'Release'):
        entry = binary / name
        data = entry.read_bytes()
        release += ' '+algorithm(data).hexdigest()+' '+str(len(data))+' '+entry.relative_to(suite).as_posix()+'\n'
(suite / 'Release').write_text(release)
gpg = ['gpg', '--homedir', str(key_home), '--batch', '--yes', '--digest-algo', 'SHA256']
subprocess.run(gpg+['--clearsign', '--output', str(suite/'InRelease'), str(suite/'Release')], check=True)
subprocess.run(gpg+['--armor', '--detach-sign', '--output', str(suite/'Release.gpg'), str(suite/'Release')], check=True)
public = subprocess.check_output(gpg+['--export'])
(repo/'vaio-artcraft-archive-keyring.gpg').write_bytes(public)
fingerprints = subprocess.check_output(gpg+['--with-colons', '--list-keys'], text=True)
fingerprint = next(line.split(':')[9] for line in fingerprints.splitlines() if line.startswith('fpr:'))
(repo/'KEY-FINGERPRINT.txt').write_text(fingerprint+'\n')
(repo/'.nojekyll').touch()
print('Staged '+str(repo)+'\nFingerprint: '+fingerprint+'\nPackage URL: '+url)
