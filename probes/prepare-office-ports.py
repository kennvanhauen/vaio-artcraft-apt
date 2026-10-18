#!/usr/bin/env python3
"""Prepare pinned spreadsheet/PDF candidate build trees, without upstream edits."""
from pathlib import Path
import difflib,io,subprocess,tarfile
root=Path(__file__).resolve().parents[1]
revisions={'gridcraft':'c30fa3f1cf324603f3bfc0171689b1d4083b40e5','pdfcraft':'98cbd38a8e0f5afe685258aa0fcab0f0012f7a8b'}
for app,revision in revisions.items():
    source=root/'upstream'/app
    actual=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if actual!=revision:raise SystemExit('Unexpected revision: '+app)
    target=root/'.build'/(app+'-port')
    if target.exists():raise SystemExit('Build tree already exists: '+app)
    target.mkdir()
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','-C',str(source),'archive','HEAD']))) as archive:
        archive.extractall(target,filter='data')
    subprocess.run(['patch','-p1','-i',str(root/'ports'/(app+'-xenial.patch'))],cwd=target,check=True)
    lock=root/'ports'/(app+'-vaio.Cargo.lock')
    if lock.exists():
        (target/'Cargo.lock').write_bytes(lock.read_bytes())
    print(target)
