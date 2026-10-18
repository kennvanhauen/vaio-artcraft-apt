#!/usr/bin/env python3
"""Verify the pinned fonts FigCraft actually embeds, including Latin manifest."""
from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parents[1];fonts=root/'.build/figcraft-fonts';revision='43913056ce82a3fdad0ef69f6b88d1dc922a8104'
entries=[]
for name in ['latin-manifest.txt','manifest.txt']:
 manifest=subprocess.check_output(['git','-C',str(root/'upstream/craft-fonts'),'show',revision+':fonts/'+name])
 assert (fonts/'fonts'/name).read_bytes()==manifest
 for line in manifest.decode().splitlines():
  if not line.strip() or line.lstrip().startswith('#'):continue
  family,style,file,scripts,licence,licence_file,digest,source=[p.strip() for p in line.split('|')]
  if 'Hans' in scripts:continue # upstream's native default unless FIGCRAFT_EMBED_CJK is requested
  data=(fonts/file).read_bytes();assert hashlib.sha256(data).hexdigest()==digest,file
  assert licence=='OFL-1.1'
  assert (fonts/licence_file).read_bytes()==subprocess.check_output(['git','-C',str(root/'upstream/craft-fonts'),'show',revision+':'+licence_file])
  entries.append(dict(family=family,style=style,file=file,licence=licence,licence_file=licence_file,sha256=digest,source=source,size=len(data)))
r=dict(revision=revision,fonts=entries,total_bytes=sum(x['size'] for x in entries));(root/'.build/figcraft-fonts-verified.json').write_text(json.dumps(r,indent=2)+'\n');print('Verified',len(entries),'font faces,',round(r['total_bytes']/1048576,1),'MiB')
