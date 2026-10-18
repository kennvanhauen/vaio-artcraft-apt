#!/usr/bin/env python3
"""Prepare project-local tools on this Apple Silicon Mac. No global installation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import urllib.request

root = Path(__file__).resolve().parents[1]
build = root / '.build'
downloads = build / 'downloads'
downloads.mkdir(parents=True, exist_ok=True)
hashes = json.loads((root / 'notes/build-input-sha256.json').read_text())
urls = {
    'rustup-init': 'https://static.rust-lang.org/rustup/dist/aarch64-apple-darwin/rustup-init',
    'zig.tar.xz': 'https://ziglang.org/download/0.14.1/zig-aarch64-macos-0.14.1.tar.xz',
    'libxcb-1.17.0.tar.xz': 'https://xcb.freedesktop.org/dist/libxcb-1.17.0.tar.xz',
    'xcb-proto-1.17.0.tar.xz': 'https://xcb.freedesktop.org/dist/xcb-proto-1.17.0.tar.xz',
}
for name, url in urls.items():
    target = downloads / name
    if not target.exists():
        urllib.request.urlretrieve(url, target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != hashes[name]:
        raise SystemExit('Checksum mismatch: ' + name)
    if name.endswith('.xz'):
        with tarfile.open(target) as archive:
            # Python 3.12+ extraction filter prevents paths outside the destination.
            if not (build / archive.getnames()[0].split('/')[0]).exists():
                archive.extractall(build, filter='data')
bootstrap = downloads / 'rustup-init'
bootstrap.chmod(0o755)
env = dict(os.environ, RUSTUP_HOME=str(build / 'rustup'), CARGO_HOME=str(build / 'cargo'))
subprocess.run([str(bootstrap), '-y', '--no-modify-path', '--profile', 'minimal',
                '--default-toolchain', '1.95.0', '--target', 'i686-unknown-linux-gnu'],
               env=env, check=True)
