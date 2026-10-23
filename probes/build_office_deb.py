#!/usr/bin/env python3
"""Package the measured spreadsheet/PDF ports as native Xenial i386 packages."""
import gzip
import hashlib
import io
import json
import lzma
from pathlib import Path
import sys
import tarfile
import tomllib

root = Path(__file__).resolve().parents[1]
specs = {
    'soundcraft': ('0.12.1~vaio1', 'e85a4801e9029c9a1f5ce536b11be65aea832ed8',
                   'SoundCraft', 'AudioVideo;Audio;AudioVideoEditing;',
                   'application/x-soundcraft;audio/x-wav;audio/flac;audio/mpeg;audio/x-aiff;'),
    'cadcraft': ('0.9.0~vaio1', '0cc66ad3066e71f2c3d4cacb7de905e79ba1c95b',
                 'CADCraft', 'Graphics;Engineering;', 'image/vnd.dxf;image/vnd.dwg;'),
    'figcraft': ('0.7.0~vaio1', 'a0d1162976fac1e4a8b8fd49a3948e9d6bad6f40',
                 'FigCraft', 'Graphics;2DGraphics;', 'application/x-figcraft;image/svg+xml;'),
    'designcraft': ('0.9.0~vaio1', 'ecd7e5d063eb12fa5e61fe61c9b8a77bb3c9110a',
                    'DesignCraft', 'Office;Publishing;',
                    'application/x-designcraft;application/vnd.adobe.indesign-idml-package;'),
    'vectorcraft': ('0.13.1~vaio1', 'a466625c8987550635cda951ebf36e08e1e80a56',
                    'VectorCraft', 'Graphics;VectorGraphics;',
                    'application/x-vectorcraft;image/svg+xml;'),
    'gridcraft': ('0.8.0~vaio1', 'c30fa3f1cf324603f3bfc0171689b1d4083b40e5',
                  'GridCraft', 'Office;Spreadsheet;',
                  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;text/csv;'),
    'deckcraft': ('0.8.0~vaio1', 'cb78440a1618e6a2c1df55dd7bff74719685518c',
                  'DeckCraft', 'Office;Presentation;',
                  'application/vnd.openxmlformats-officedocument.presentationml.presentation;application/vnd.openxmlformats-officedocument.presentationml.slideshow;application/vnd.openxmlformats-officedocument.presentationml.template;application/x-deckcraft;'),
    'pdfcraft': ('0.9.0~vaio1', '98cbd38a8e0f5afe685258aa0fcab0f0012f7a8b',
                 'PdfCraft', 'Office;Viewer;', 'application/pdf;'),
}
app = sys.argv[1]
version, revision, title, categories, mime = specs[app]
from update_package_spec import candidate_spec
version, revision = candidate_spec(root, app, version, revision)
package = app+'-vaio'
source = root/'upstream'/app
files = {}

def add(name, data, mode=0o644):
    files[name] = (data, mode)

hashes = {}
for name in (app, app+'-cli'):
    target_dir = 'soundcraft-target' if app == 'soundcraft' else 'wordcraft-target'
    data = (root/'.build'/target_dir/'i686-unknown-linux-gnu/release'/name).read_bytes()
    if data[:6] != b'\x7fELF\x01\x01' or int.from_bytes(data[18:20], 'little') != 3:
        raise SystemExit('Not an i386 ELF: '+name)
    if b'/Users/kennvanhauen' in data:
        raise SystemExit('Build-machine path embedded in binary: '+name)
    hashes[name] = hashlib.sha256(data).hexdigest()
    add('usr/lib/'+package+'/bin/'+name, data, 0o755)
    wrapper = '#!/bin/sh\n'
    if app == 'figcraft':
        wrapper += 'export FIGCRAFT_STATIC_CARET="${FIGCRAFT_STATIC_CARET:-1}"\n'
    if app == 'designcraft':
        wrapper += 'export DESIGNCRAFT_STATIC_CARET="${DESIGNCRAFT_STATIC_CARET:-1}"\n'
    if app == 'pdfcraft':
        wrapper += 'export PDFCRAFT_RENDERER=gl\n'
    if app == 'deckcraft':
        wrapper += 'export DECKCRAFT_STATIC_CARET="${DECKCRAFT_STATIC_CARET:-1}"\n'
        wrapper += 'if test \"${DECKCRAFT_ENABLE_AUDIO:-0}\" != 1; then export DECKCRAFT_NO_AUDIO=1; else unset DECKCRAFT_NO_AUDIO; fi\n'
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
if app == 'soundcraft':
    add('usr/share/mime/packages/soundcraft-vaio.xml', b'''<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-soundcraft">
    <comment>SoundCraft audio session</comment><glob pattern="*.scraft"/>
  </mime-type>
</mime-info>
''')
if app == 'figcraft':
    add('usr/share/mime/packages/figcraft-vaio.xml', b'<?xml version="1.0" encoding="UTF-8"?>\n<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info"><mime-type type="application/x-figcraft"><comment>FigCraft interface design</comment><glob pattern="*.figcraft"/></mime-type></mime-info>\n')
if app == 'designcraft':
    add('usr/share/mime/packages/designcraft-vaio.xml', b'''<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-designcraft">
    <comment>DesignCraft page layout</comment>
    <glob pattern="*.designcraft"/>
  </mime-type>
</mime-info>
''')
if app == 'vectorcraft':
    add('usr/share/mime/packages/vectorcraft-vaio.xml', b'''<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-vectorcraft">
    <comment>VectorCraft illustration</comment>
    <glob pattern="*.vectorcraft"/>
    <glob pattern="*.drawcraft"/>
  </mime-type>
</mime-info>
''')
if app == 'deckcraft':
    add('usr/share/mime/packages/deckcraft-vaio.xml', b'''<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-deckcraft">
    <comment>DeckCraft presentation</comment>
    <glob pattern="*.deckcraft"/>
  </mime-type>
</mime-info>
''')
icon=source/'assets/app-icon'/('icon.svg' if app == 'soundcraft' else app+'.svg')
if icon.exists():
    add('usr/share/icons/hicolor/scalable/apps/'+package+'.svg', icon.read_bytes())
elif app == 'cadcraft':
    add('usr/share/icons/hicolor/256x256/apps/'+package+'.png', (source/'assets/app-icon/cadcraft-256.png').read_bytes())
else:
    add('usr/share/icons/hicolor/256x256/apps/'+package+'.png', (source/'assets/app-icon/hicolor/256x256/apps'/('ai.storyteller.'+app+'.png')).read_bytes())
doc = 'usr/share/doc/'+package+'/'
for name in ('LICENSE-MIT', 'LICENSE-APACHE', 'NOTICE', 'ASSETS.md', 'ATTRIBUTION.md', 'ATTRIBUTION.toml'):
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
see upstream ASSETS.md or ATTRIBUTION.md. See build.json for optional font input details.
A private libxcb 1.17.0 is bundled under its original permissive notices.
'''.encode())
metadata = dict(package_version=version, source_revision=revision, rust='1.95.0',
                zig='0.14.1', target='i686-unknown-linux-gnu', cpu='atom',
                glibc_target='2.23', renderer='Glow', private_libxcb='1.17.0',
                binary_sha256=hashes, port_patch_sha256=hashlib.sha256(
                    (root/'ports'/(app+'-xenial.patch')).read_bytes()).hexdigest())
if app == 'soundcraft':
    fonts_source=next((root/'.build/cargo/registry/src').glob('*/epaint_default_fonts-0.36.2/fonts'))
    for path in fonts_source.glob('*.txt'):
        add(doc+'egui-font-notices/'+path.name,path.read_bytes())
    metadata['fonts']='egui defaults plus existing system fonts loaded at runtime; no system fonts redistributed'
    metadata['default_audio_buffer_frames']=4096
    metadata['vaio_meter_refresh_hz']=12
if app in ('deckcraft', 'vectorcraft', 'designcraft', 'figcraft', 'cadcraft'):
    for path in (source/'licenses').rglob('*'):
        if path.is_file():
            add(doc+str(path.relative_to(source)),path.read_bytes())
    registry=root/'.build/cargo/registry/src'
    fonts_source=next(registry.glob('*/epaint_default_fonts-0.36.2/fonts'))
    for path in fonts_source.glob('*.txt'):
        add(doc+'egui-font-notices/'+path.name,path.read_bytes())
    verified=json.loads((root/'.build'/(app+'-fonts-verified.json')).read_text())
    metadata['craft_fonts_revision']=verified['revision']
    metadata['embedded_font_faces']=len(verified['fonts'])
    font_root = root/'.build'/(app+'-fonts') if app in ('vectorcraft','designcraft','figcraft','cadcraft') else root/'upstream/craft-fonts'
    add(doc+'craft-fonts/ATTRIBUTION.md', (font_root/'ATTRIBUTION.md').read_bytes())
    add(doc+'craft-fonts/verified-fonts.json', (json.dumps(verified,indent=2)+'\n').encode())
    for entry in verified['fonts']:
        licence=entry['licence_file']
        add(doc+'craft-fonts/'+licence,(font_root/licence).read_bytes())
if app == 'cadcraft':
    used_lock = tomllib.loads((root/'.build/cadcraft-port/Cargo.lock').read_text())
    if {p['version'] for p in used_lock['package'] if p['name'] == 'acadrust'} != {'0.6.4'}:
        raise SystemExit('acadrust changed: review and update the MPL source notice before packaging')
    dep=next((root/'.build/cargo/registry/src').glob('*/acadrust-0.6.4'))
    add(doc+'acadrust-MPL-2.0.txt',(dep/'LICENSE').read_bytes())
    add(doc+'acadrust-SOURCE.txt',b'Unmodified acadrust 0.6.4, Mozilla Public License 2.0.\nCorresponding source: https://crates.io/api/v1/crates/acadrust/0.6.4/download\nRepository: https://github.com/hakanaktt/acadrust\nCrate archive SHA256: 94862189cab6e282ed0433a801a216cd1a712953813284a48fa81c67223e38f6\n')
add(doc+'build.json', (json.dumps(metadata, indent=2)+'\n').encode())
depends = ('zenity, cups-client, libc6 (>= 2.23), libx11-6, libx11-xcb1, libxau6, '
           'libxcb1, libxkbcommon0, libxkbcommon-x11-0, libxrandr2, libxi6, '
           'libxcursor1, libxext6, libgl1-mesa-glx, libgl1-mesa-dri, libegl1-mesa')
if app == 'deckcraft':depends += ', libasound2 (>= 1.1.0), shared-mime-info, xscreensaver'
if app == 'soundcraft':depends += ', libasound2 (>= 1.1.0), shared-mime-info, fontconfig'
if app in ('vectorcraft','designcraft','figcraft','cadcraft'):depends += ', shared-mime-info'
control = f'''Package: {package}
Version: {version}
Architecture: i386
Section: {'sound' if app == 'soundcraft' else 'graphics' if app == 'vectorcraft' else 'editors'}
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
    if directories and app in ('vectorcraft','designcraft','figcraft','cadcraft'):
        # Xenial dpkg supports XZ; preset 6 keeps decode memory modest on the 2 GB VAIO.
        return lzma.compress(buffer.getvalue(), format=lzma.FORMAT_XZ, preset=6)
    return gzip.compress(buffer.getvalue(), compresslevel=6, mtime=0)

parts = [('debian-binary', b'2.0\n'),
         ('control.tar.gz', archive({'control': (control, 0o644), 'md5sums': (md5, 0o644)})),
         ('data.tar.xz' if app in ('vectorcraft','designcraft','figcraft','cadcraft') else 'data.tar.gz', archive(files, True))]
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
