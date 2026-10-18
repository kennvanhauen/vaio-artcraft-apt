#!/usr/bin/env python3
"""Verify the native font manifest and notices against the pinned font archive."""
from pathlib import Path
import hashlib, json, subprocess
root = Path(__file__).resolve().parents[1]
fonts = root/'.build/vectorcraft-fonts'
revision = 'a71c20e30af613287c504f7e685ca8fad77752bc'
manifest = subprocess.check_output(['git','-C',str(root/'upstream/craft-fonts'),'show',revision+':fonts/manifest.txt'])
assert (fonts/'fonts/manifest.txt').read_bytes() == manifest
entries = []
for line in manifest.decode().splitlines():
    if not line.strip() or line.lstrip().startswith('#'):
        continue
    family, style, file, scripts, licence, licence_file, digest, source = [p.strip() for p in line.split('|')]
    data = (fonts/file).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest, file
    assert licence == 'OFL-1.1'
    expected = subprocess.check_output(['git','-C',str(root/'upstream/craft-fonts'),'show',revision+':'+licence_file])
    assert (fonts/licence_file).read_bytes() == expected
    entries.append(dict(family=family,style=style,file=file,scripts=scripts,licence=licence,licence_file=licence_file,sha256=digest,source=source,size=len(data)))
result = dict(revision=revision,fonts=entries,total_bytes=sum(e['size'] for e in entries))
(root/'.build/vectorcraft-fonts-verified.json').write_text(json.dumps(result,indent=2)+'\n')
print('Verified %d native font faces, %.1f MiB, with original notices' % (len(entries),result['total_bytes']/1048576))
