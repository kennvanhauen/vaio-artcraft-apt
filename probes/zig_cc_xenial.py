#!/usr/bin/env python3
"""Keep third-party cc-rs probes on the explicit Atom/glibc 2.23 Zig target."""
import os
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
arguments=[]
for arg in sys.argv[1:]:
    if arg.startswith('--target='):
        target=arg.split('=',1)[1]
        if target not in ('i686-unknown-linux-gnu','i686-linux-gnu','x86-unknown-linux-gnu.2.23','x86-linux-gnu.2.23'):
            raise SystemExit('Conflicting C compiler target: '+target)
        continue
    arguments.append(arg)
if arguments==['-dumpmachine']:
    print('i686-linux-gnu')
    raise SystemExit(0)
os.environ['ZIG_GLOBAL_CACHE_DIR']=str(root/'.build/zig-cache')
os.environ['ZIG_LOCAL_CACHE_DIR']=str(root/'.build/zig-local-cache')
zig=root/'.build/zig-aarch64-macos-0.14.1/zig'
os.execv(str(zig),[str(zig),'cc','-target','x86-linux-gnu.2.23','-mcpu=atom',
    '-L'+str(root/'.build/sysroot/usr/lib/i386-linux-gnu')]+arguments)
