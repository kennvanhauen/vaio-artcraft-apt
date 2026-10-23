#!/usr/bin/env python3
"""Native Xenial i386 package for the VAIO launcher with a root-owned APT helper."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

root = Path(__file__).resolve().parents[1]
from update_package_spec import candidate_spec
version, revision = candidate_spec(root, 'launcher', '0.5.1~vaio9', '9cef5d2a0f207da50d31547a726057ea40f7e5b4')
binary = (root / '.build/wordcraft-target/i686-unknown-linux-gnu/release/artcraft-launcher-vaio').read_bytes()
if binary[:6] != b'\x7fELF\x01\x01' or int.from_bytes(binary[18:20], 'little') != 3:
    raise SystemExit('Not an i386 ELF executable')
if b'/Users/kennvanhauen' in binary:
    raise SystemExit('Build-machine path embedded in public binary')
files = {}
def add(name, data, mode=0o644):
    files[name] = data,mode
add('usr/lib/artcraft-launcher-vaio/bin/launcher', binary, 0o755)
add('usr/lib/artcraft-launcher-vaio/lib/libxcb.so.1', (root/'.build/private-lib/libxcb.so.1').read_bytes())
add('usr/lib/artcraft-launcher-vaio/apt-action', (root/'ports/launcher-vaio/apt-action').read_bytes(), 0o755)
add('usr/bin/vaio-app-launcher', b'''#!/bin/sh
export LD_LIBRARY_PATH="/usr/lib/artcraft-launcher-vaio/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec /usr/lib/artcraft-launcher-vaio/bin/launcher "$@"
''', 0o755)
add('usr/share/applications/vaio-app-launcher.desktop', b'''[Desktop Entry]
Type=Application
Name=VAIO App Launcher
Comment=Open and manage the VAIO application previews with APT
Exec=vaio-app-launcher
Icon=vaio-app-launcher
Terminal=false
StartupNotify=true
Categories=Utility;System;
''')
add('usr/share/icons/hicolor/scalable/apps/vaio-app-launcher.svg', (root/'ports/launcher-vaio/launcher.svg').read_bytes())
doc = 'usr/share/doc/artcraft-launcher-vaio/'
for name in ['LICENSE-MIT','LICENSE-APACHE','NOTICE','ATTRIBUTION.md']:
    add(doc+name,(root/'upstream/craft-launcher'/name).read_bytes())
for path in sorted((root/'upstream/craft-launcher/assets/fonts').glob('OFL-*.txt')):
    add(doc+path.name,path.read_bytes())
add(doc+'ATTRIBUTION-VAIO.md', (root/'ports/launcher-vaio/ATTRIBUTION.md').read_bytes())
add(doc+'libxcb-COPYING', (root/'.build/libxcb-1.17.0/COPYING').read_bytes())
add(doc+'README.VAIO', b'''VAIO App Launcher is an unofficial modification based on ArtCraft Launcher.
The original ArtCraft trademarks have been removed and replaced with a generic tile icon.
Offers WordCraft, GridCraft, PdfCraft, DeckCraft, VectorCraft, DesignCraft, FigCraft, CADCraft and SoundCraft VAIO previews. Uses Glow and reduced motion.
Package state is read from dpkg. Refresh fetches and verifies signed project APT metadata
into the user cache, without root access or a system-wide update. Cached results remain
available offline; a failed refresh is reported. The existing system Check & Install
Updates frontend also sees these packages through the permanent signed APT source.
Install/update/remove buttons use a root-owned, allowlisted APT helper after a visible
administrator prompt and confirmation in a terminal. Update All queues selected apps
into a shared APT transaction. Documents and settings stay.
The launcher itself is updated and removed through APT, without a separate updater.
View/theme/language and window preferences persist between runs and recover from
invalid data. No autostart, tray daemon or downloaded privileged helper is installed.
''')
metadata={'package_version':version,'upstream_revision':revision,
 'binary_sha256':hashlib.sha256(binary).hexdigest(),'target':'i686-unknown-linux-gnu',
 'cpu':'atom','glibc_target':'2.23','renderer':'Glow','private_libxcb':'1.17.0',
 'port_patch_sha256':hashlib.sha256((root/'ports/launcher-xenial.patch').read_bytes()).hexdigest()}
add(doc+'build.json',(json.dumps(metadata,indent=2)+'\n').encode())
control=('''Package: artcraft-launcher-vaio
Version: VERSION
Architecture: i386
Section: utils
Priority: optional
Maintainer: VAIO local build <vaio@localhost>
Installed-Size: SIZE
Depends: apt, gksu, xterm, libc6 (>= 2.23), libx11-6, libx11-xcb1, libxau6, libxcb1, libxkbcommon0, libxkbcommon-x11-0, libxrandr2, libxi6, libxcursor1, libxext6, libgl1-mesa-glx, libgl1-mesa-dri, libegl1-mesa
Description: VAIO App Launcher using native APT-managed application previews
 Unofficial adaptation based on ArtCraft Launcher for Ubuntu Xenial i386.
 Uses Glow, a private XCB library and reduced motion on the Atom VAIO P.
'''.replace('VERSION',version).replace('SIZE',str((sum(len(v[0]) for v in files.values())+1023)//1024))).encode()
md5=''.join(hashlib.md5(data).hexdigest()+'  '+name+'\n' for name,(data,_) in sorted(files.items())).encode()
def archive(entries, directories=False):
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w',format=tarfile.GNU_FORMAT) as output:
        if directories:
            parents={str(p) for name in entries for p in Path(name).parents if str(p)!='.'}
            for name in sorted(parents):
                info=tarfile.TarInfo('./'+name+'/'); info.type=tarfile.DIRTYPE; info.mode=0o755
                info.uid=info.gid=0; info.uname=info.gname='root'; info.mtime=1792281600
                output.addfile(info)
        for name,(data,mode) in sorted(entries.items()):
            info=tarfile.TarInfo('./'+name); info.size=len(data); info.mode=mode
            info.uid=info.gid=0; info.uname=info.gname='root'; info.mtime=1792281600
            output.addfile(info,io.BytesIO(data))
    return gzip.compress(buffer.getvalue(),compresslevel=6,mtime=0)
parts=[('debian-binary',b'2.0\n'),('control.tar.gz',archive({'control':(control,0o644),'md5sums':(md5,0o644)})),('data.tar.gz',archive(files,True))]
destination=root/'dist'/('artcraft-launcher-vaio_'+version+'_i386.deb')
with destination.open('wb') as out:
    out.write(b'!<arch>\n')
    for name,data in parts:
        out.write('{:<16}{:<12}{:<6}{:<6}{:<8o}{:<10}`\n'.format(name+'/',0,0,0,0o100644,len(data)).encode())
        out.write(data)
        if len(data)%2:out.write(b'\n')
destination.with_suffix('.build.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(str(destination)+'\nSHA256 '+hashlib.sha256(destination.read_bytes()).hexdigest())
