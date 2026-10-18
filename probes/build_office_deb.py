#!/usr/bin/env python3
"""Package the measured spreadsheet/PDF ports as native Xenial i386 packages."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tomllib

root = Path(__file__).resolve().parents[1]
specs = {
    'gridcraft': ('0.8.0~vaio1', 'c30fa3f1cf324603f3bfc0171689b1d4083b40e5',
                  'GridCraft', 'Office;Spreadsheet;',
                  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;text/csv;'),
    'pdfcraft': ('0.9.0~vaio1', '98cbd38a8e0f5afe685258aa0fcab0f0012f7a8b',
                 'PdfCraft', 'Office;Viewer;', 'application/pdf;'),
}
app = sys.argv[1]
version, revision, title, categories, mime = specs[app]
package = app+'-vaio'
source = root/'upstream'/app
files = {}

def add(name, data, mode=0o644):
    files[name] = (data, mode)

hashes = {}
for name in (app, app+'-cli'):
    data = (root/'.build/wordcraft-target/i686-unknown-linux-gnu/release'/name).read_bytes()
    if data[:6] != b'\x7fELF\x01\x01' or int.from_bytes(data[18:20], 'little') != 3:
        raise SystemExit('Not an i386 ELF: '+name)
    if b'/Users/kennvanhauen' in data:
        raise SystemExit('Build-machine path embedded in binary: '+name)
    hashes[name] = hashlib.sha256(data).hexdigest()
    add('usr/lib/'+package+'/bin/'+name, data, 0o755)
    wrapper = '#!/bin/sh\n'
    if app == 'pdfcraft':
        wrapper += 'export PDFCRAFT_RENDERER=gl\n'
    wrapper += 'export LD_LIBRARY_PATH="/usr/lib/'+package+'/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n'
    wrapper += 'exec /usr/lib/'+package+'/bin/'+name+' "$@"\n'
    command = package if name == app else package+'-cli'
    add('usr/bin/'+command, wrapper.encode(), 0o755)
add('usr/lib/'+package+'/lib/libxcb.so.1', (root/'.build/private-lib/libxcb.so.1').read_bytes())
desktop = f'''[Desktop Entry]
Type=Application
Name={title} (VAIO preview)
Comment={title} adapted for the Sony VAIO
Exec={package} %F
Icon={package}
Terminal=false
StartupNotify=true
Categories={categories}
MimeType={mime}
'''
add('usr/share/applications/'+package+'.desktop', desktop.encode())
add('usr/share/icons/hicolor/scalable/apps/'+package+'.svg', (source/'assets/app-icon'/(app+'.svg')).read_bytes())
doc = 'usr/share/doc/'+package+'/'
for name in ('LICENSE-MIT', 'LICENSE-APACHE', 'NOTICE', 'ATTRIBUTION.md', 'ATTRIBUTION.toml'):
    if (source/name).exists():
        add(doc+name, (source/name).read_bytes())
for path in sorted((source/'assets').rglob('*.txt')):
    if path.name.startswith(('OFL-', 'LICENSE')):
        add(doc+str(path.relative_to(source)), path.read_bytes())
add(doc+'libxcb-COPYING', (root/'.build/libxcb-1.17.0/COPYING').read_bytes())
if app == 'pdfcraft':
    manifest = tomllib.loads((source/'ATTRIBUTION.toml').read_text())
    for model in manifest['fetched']:
        if model.get('kind') != 'model':
            continue
        data = (root/'.build/pdfcraft-models'/model['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == model['sha256']
        add('usr/share/pdfcraft/models/'+model['file'], data)
    licence = (root/'.build/pdfcraft-models/CC-BY-SA-4.0.txt').read_bytes()
    assert hashlib.sha256(licence).hexdigest() == '28a9529c7d0bb4dc51f4bf5c116a3d16ef247a052f7591466768ddf563fd1cf5'
    add(doc+'CC-BY-SA-4.0.txt', licence)
    add(doc+'OCR-MODELS.md', b'Unmodified Ocrs models by Robert Knight, trained on HierText.\nSource: https://github.com/robertknight/ocrs-models\nLicense: CC-BY-SA-4.0; attribution and pinned hashes in ATTRIBUTION.toml.\n')
add(doc+'README.VAIO', (root/'ports'/('README.'+app.upper())).read_bytes())
add(doc+'ATTRIBUTION-VAIO.md', f'''Unofficial {title} modification for Ubuntu Xenial i386, built from
https://github.com/storytold/{app} at {revision}.
Downstream code is licensed MIT OR Apache-2.0, like the original project.
Original ArtCraft trademark graphics are not used in this modified release.
The application icon is upstream contributor-original MIT OR Apache-2.0 artwork;
see assets/app-icon/LICENSE.txt. No optional craft-fonts input is embedded.
A private libxcb 1.17.0 is bundled under its original permissive notices.
'''.encode())
metadata = dict(package_version=version, source_revision=revision, rust='1.95.0',
                zig='0.14.1', target='i686-unknown-linux-gnu', cpu='atom',
                glibc_target='2.23', renderer='Glow', private_libxcb='1.17.0',
                binary_sha256=hashes, port_patch_sha256=hashlib.sha256(
                    (root/'ports'/(app+'-xenial.patch')).read_bytes()).hexdigest())
add(doc+'build.json', (json.dumps(metadata, indent=2)+'\n').encode())
depends = ('zenity, cups-client, libc6 (>= 2.23), libx11-6, libx11-xcb1, libxau6, '
           'libxcb1, libxkbcommon0, libxkbcommon-x11-0, libxrandr2, libxi6, '
           'libxcursor1, libxext6, libgl1-mesa-glx, libgl1-mesa-dri, libegl1-mesa')
control = f'''Package: {package}
Version: {version}
Architecture: i386
Section: editors
Priority: optional
Maintainer: VAIO local build <vaio@localhost>
Installed-Size: {(sum(len(v[0]) for v in files.values())+1023)//1024}
Depends: {depends}
Description: {title} preview adapted for Ubuntu Xenial i386 on the Sony VAIO
 Unofficial native 32-bit build using Glow and a private XCB library.
 APT owns application files; existing user documents and settings are retained.
'''.encode()
md5 = ''.join(hashlib.md5(data).hexdigest()+'  '+name+'\n'
              for name, (data, _) in sorted(files.items())).encode()

def archive(entries, directories=False):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.GNU_FORMAT) as output:
        if directories:
            parents = {str(p) for name in entries for p in Path(name).parents if str(p) != '.'}
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

parts = [('debian-binary', b'2.0\n'),
         ('control.tar.gz', archive({'control': (control, 0o644), 'md5sums': (md5, 0o644)})),
         ('data.tar.gz', archive(files, True))]
destination = root/'dist'/(package+'_'+version+'_i386.deb')
with destination.open('wb') as out:
    out.write(b'!<arch>\n')
    for name, data in parts:
        header = '{:<16}{:<12}{:<6}{:<6}{:<8o}{:<10}`\n'.format(name+'/', 0, 0, 0, 0o100644, len(data)).encode()
        assert len(header) == 60
        out.write(header)
        out.write(data)
        if len(data) % 2:
            out.write(b'\n')
destination.with_suffix('.build.json').write_text(json.dumps(metadata, indent=2)+'\n')
print(str(destination)+'\nSHA256 '+hashlib.sha256(destination.read_bytes()).hexdigest())
