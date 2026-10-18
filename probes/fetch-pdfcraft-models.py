#!/usr/bin/env python3
"""Fetch only PdfCraft's pinned, attributed OCR models and verified licence."""
import hashlib
from pathlib import Path
import tomllib
import urllib.request

root=Path(__file__).resolve().parents[1]
manifest=tomllib.loads((root/'upstream/pdfcraft/ATTRIBUTION.toml').read_text())
output=root/'.build/pdfcraft-models';output.mkdir(parents=True,exist_ok=True)
def fetch(url,name,digest):
    target=output/name
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==digest:
        return
    request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 VAIO-port-builder'})
    with urllib.request.urlopen(request,timeout=60) as response:data=response.read(32*1024*1024)
    if hashlib.sha256(data).hexdigest()!=digest:raise SystemExit('Hash mismatch: '+name)
    target.write_bytes(data)
for model in manifest['fetched']:
    if model.get('kind')!='model':continue
    fetch(model['url'],model['file'],model['sha256'])
    fetch(model['licence_url'],'CC-BY-SA-4.0.txt',model['licence_sha256'])
    print(model['file']+': verified')
