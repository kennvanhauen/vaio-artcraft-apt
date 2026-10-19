#!/usr/bin/env python3
"""Build a Xenial-compatible i386 .deb on the Mac without privileged tools."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile

root = Path(__file__).resolve().parents[1]
version = sys.argv[1] if len(sys.argv) > 1 else '0.8.0~vaio5'
if not os.environ.get('VAIO_PACKAGE_SPEC') and version not in ('0.8.0~vaio1', '0.8.0~vaio2', '0.8.0~vaio3', '0.8.0~vaio4', '0.8.0~vaio5'):
    raise SystemExit('Unknown preview version')
from update_package_spec import candidate_spec
version, revision = candidate_spec(root, 'wordcraft', version, 'd6f20f93fd22deb441b2216ecfd65acb15ea8b64')
files = {}

def add(name, data, mode=0o644):
    files[name] = (data, mode)

for name in ('wordcraft', 'wordcraft-cli'):
    binary = (root / '.build/test-runtime/bin' / name).read_bytes()
    if binary[:6] != b'\x7fELF\x01\x01' or int.from_bytes(binary[18:20], 'little') != 3:
        raise SystemExit('Not a Linux i386 ELF executable: '+name)
    add('usr/lib/wordcraft-vaio/bin/'+name, binary, 0o755)
    wrapper_name = 'wordcraft-vaio' if name == 'wordcraft' else 'wordcraft-vaio-cli'
    wrapper = '''#!/bin/sh
export WORDCRAFT_STATIC_CARET=1
export LD_LIBRARY_PATH="/usr/lib/wordcraft-vaio/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec /usr/lib/wordcraft-vaio/bin/''' + name + ''' "$@"
'''
    add('usr/bin/'+wrapper_name, wrapper.encode(), 0o755)
add('usr/lib/wordcraft-vaio/lib/libxcb.so.1', (root / '.build/private-lib/libxcb.so.1').read_bytes())
add('usr/share/applications/wordcraft-vaio.desktop', b'''[Desktop Entry]
Type=Application
Name=WordCraft (VAIO preview)
Comment=Write and edit documents on the Sony VAIO
Exec=wordcraft-vaio %F
Icon=wordcraft-vaio
Terminal=false
StartupNotify=true
Categories=Office;WordProcessor;
MimeType=application/vnd.openxmlformats-officedocument.wordprocessingml.document;application/vnd.oasis.opendocument.text;application/rtf;text/rtf;text/markdown;text/html;text/plain;
''')
add('usr/share/icons/hicolor/scalable/apps/wordcraft-vaio.svg',
    (root / 'upstream/wordcraft/assets/app-icon/wordcraft.svg').read_bytes())
doc = 'usr/share/doc/wordcraft-vaio/'
for license_file in ('LICENSE-MIT', 'LICENSE-APACHE', 'NOTICE', 'ATTRIBUTION.md'):
    add(doc+license_file, (root / 'upstream/wordcraft' / license_file).read_bytes())
for license_file in sorted((root / 'upstream/wordcraft/assets/fonts').glob('OFL-*.txt')):
    add(doc+license_file.name, license_file.read_bytes())
add(doc+'libxcb-COPYING', (root / '.build/libxcb-1.17.0/COPYING').read_bytes())
add(doc+'copyright', b'''WordCraft: https://github.com/storytold/wordcraft
License: MIT OR Apache-2.0; see LICENSE-MIT and LICENSE-APACHE.
Bundled private libxcb: https://xcb.freedesktop.org/
License: permissive X11/MIT notices; see libxcb-COPYING.
Original application icon is from the pinned WordCraft source tree.
''')
add(doc+'README.VAIO', (root / 'ports/README.WORDCRAFT').read_bytes())
metadata = {
    'package_version': version,
    'source_revision': revision,
    'rust': '1.95.0', 'zig': '0.14.1', 'target': 'i686-unknown-linux-gnu',
    'cpu': 'atom', 'glibc_target': '2.23', 'renderer': 'Glow',
    'private_libxcb': '1.17.0',
    'port_patch_sha256': hashlib.sha256((root / 'ports/wordcraft-xenial.patch').read_bytes()).hexdigest(),
    'binary_sha256': {name: hashlib.sha256(files['usr/lib/wordcraft-vaio/bin/'+name][0]).hexdigest()
                      for name in ('wordcraft', 'wordcraft-cli')},
}
add(doc+'build.json', (json.dumps(metadata, indent=2)+'\n').encode())
add(doc+'package-revision', (version+'\n').encode())
installed_size = (sum(len(data) for data, _ in files.values())+1023)//1024
control = '''Package: wordcraft-vaio
Version: VERSION
Section: editors
Priority: optional
Architecture: i386
Maintainer: VAIO local build <vaio@localhost>
Installed-Size: SIZE
Depends: zenity, cups-client, libc6 (>= 2.23), libx11-6, libx11-xcb1, libxau6, libxcb1, libxkbcommon0, libxkbcommon-x11-0, libxrandr2, libxi6, libxcursor1, libxext6, libgl1-mesa-glx, libgl1-mesa-dri, libegl1-mesa
Description: WordCraft preview adapted for the Sony VAIO P and Ubuntu Xenial
 Experimental native 32-bit build with a software-rendering profile and
 a private compatible XCB library. Package-managed application files only.
'''.replace('VERSION', version).replace('SIZE', str(installed_size)).encode()
md5sums = ''.join(hashlib.md5(data).hexdigest()+'  '+name+'\n'
                  for name, (data, _) in sorted(files.items())).encode()

def archive(entries, directories=False):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.GNU_FORMAT) as output:
        if directories:
            parents = set()
            for name in entries:
                parents.update(str(parent) for parent in Path(name).parents if str(parent) != '.')
            for name in sorted(parents):
                info = tarfile.TarInfo('./'+name+'/')
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                info.uid = info.gid = 0
                info.uname = info.gname = 'root'
                info.mtime = 1792281600
                output.addfile(info)
        for name, (data, mode) in sorted(entries.items()):
            info = tarfile.TarInfo('./'+name)
            info.size, info.mode = len(data), mode
            info.uid = info.gid = 0
            info.uname = info.gname = 'root'
            info.mtime = 1792281600
            output.addfile(info, io.BytesIO(data))
    return gzip.compress(buffer.getvalue(), compresslevel=6, mtime=0)

members = [('debian-binary', b'2.0\n'),
           ('control.tar.gz', archive({'control': (control, 0o644), 'md5sums': (md5sums, 0o644)})),
           ('data.tar.gz', archive(files, directories=True))]
destination = root / 'dist' / ('wordcraft-vaio_'+version+'_i386.deb')
destination.parent.mkdir(exist_ok=True)
with destination.open('wb') as output:
    output.write(b'!<arch>\n')
    for name, data in members:
        header = '{:<16}{:<12}{:<6}{:<6}{:<8o}{:<10}`\n'.format(name+'/', 0, 0, 0, 0o100644, len(data)).encode()
        if len(header) != 60:
            raise SystemExit('Invalid ar member header')
        output.write(header)
        output.write(data)
        if len(data) % 2:
            output.write(b'\n')
(destination.with_suffix('.build.json')).write_text(json.dumps(metadata, indent=2)+'\n')
print(destination)
print('SHA256 '+hashlib.sha256(destination.read_bytes()).hexdigest())
