"""Explicit candidate metadata shared by the three package builders."""
import json
import os
from pathlib import Path
import re
import subprocess


def candidate_spec(root, app, version, revision):
    filename = os.environ.get('VAIO_PACKAGE_SPEC')
    if not filename:
        return version, revision
    spec = json.loads(Path(filename).read_text())
    if spec['app'] != app:
        raise SystemExit('Candidate specification belongs to another app')
    version, revision = spec['version'], spec['revision']
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}~vaio[1-9][0-9]*', version):
        raise SystemExit('Unsupported candidate Debian version')
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise SystemExit('Candidate must use a complete source commit')
    source = root/'upstream'/('craft-launcher' if app == 'launcher' else app)
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != revision:
        raise SystemExit('Candidate source does not match package metadata')
    return version, revision
