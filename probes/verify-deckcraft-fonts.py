#!/usr/bin/env python3
"""Verify every font DeckCraft embeds against its pinned original manifest."""
import hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];fonts=root/'upstream/craft-fonts'
revision='43913056ce82a3fdad0ef69f6b88d1dc922a8104'
assert subprocess.check_output(['git','-C',str(fonts),'rev-parse','HEAD'],text=True).strip()==revision
excluded={'Source Sans 3','Source Serif 4','Source Han Sans','Source Han Serif','Noto Sans CJK SC'}
entries=[]
for manifest in ['latin-manifest.txt','manifest.txt']:
    for line in (fonts/'fonts'/manifest).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        family,style,file,scripts,licence,licence_file,digest,source=[part.strip() for part in line.split(' | ')]
        if family in excluded:continue
        data=(fonts/file).read_bytes()
        assert hashlib.sha256(data).hexdigest()==digest,file
        assert licence=='OFL-1.1' and (fonts/licence_file).is_file(),file
        entries.append(dict(family=family,style=style,file=file,sha256=digest,
                            licence=licence,licence_file=licence_file,source=source,size=len(data)))
result=dict(revision=revision,fonts=entries,total_bytes=sum(e['size'] for e in entries))
(root/'.build/deckcraft-fonts-verified.json').write_text(json.dumps(result,indent=2)+'\n')
print('Verified %d fonts, %.1f MiB; prohibited families excluded'%(len(entries),result['total_bytes']/1048576))
