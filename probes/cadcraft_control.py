"""Read only the owned test session's CADCraft control token; never log it."""
import os
from pathlib import Path
import re
import time


def control_token(env, port, timeout=10):
    root = Path(env['XDG_RUNTIME_DIR']) if env.get('XDG_RUNTIME_DIR') else Path(env['HOME'])/'.cache'
    path = root/('cadcraft-control-%d.token' % port)
    until = time.monotonic()+timeout
    while time.monotonic() < until:
        try:
            status = path.stat()
            assert status.st_uid == os.getuid() and not status.st_mode & 0o077, 'Control token is not owner-only'
            token = path.read_text().strip()
            if re.fullmatch(r'[0-9a-f]{64}', token):
                return token
        except FileNotFoundError:
            pass
        time.sleep(.1)
    raise RuntimeError('Owned CADCraft session token was not issued')
