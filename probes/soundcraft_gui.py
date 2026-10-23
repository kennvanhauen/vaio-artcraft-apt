#!/usr/bin/python3
"""Isolated Xenial GUI, native-picker, idle and crash-recovery acceptance.

No audio devices, personal media or installed profiles are used. Run after the
headless probe, under an outer process-group timeout. Python 3.5 compatible.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import tempfile
import time
import traceback


class App:
    def __init__(self, binary, base):
        self.binary, self.base = binary, base
        (base/'documents').mkdir(exist_ok=True)
        self.env = dict(os.environ, DISPLAY=':0', SOUNDCRAFT_CONFIG_DIR=str(base/'profile'),
                        VAIO_ARTCRAFT_DOCUMENTS=str(base/'documents'),
                        XDG_CONFIG_HOME=str(base/'config'), XDG_DATA_HOME=str(base/'data'),
                        XDG_CACHE_HOME=str(base/'cache'))
        self.process = None
        self.serial = 0

    def start(self):
        subprocess.call(['xscreensaver-command', '-deactivate'], env=self.env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log = self.base/('launch-%d.log' % self.serial)
        self.stream = log.open('w')
        self.process = subprocess.Popen([str(self.binary), '--no-audio', '--control', '0'],
                                        cwd=str(self.base), env=self.env, stdout=self.stream, stderr=self.stream)
        until = time.monotonic()+30
        while time.monotonic() < until:
            assert self.process.poll() is None, log.read_text()
            m = re.search(r'SOUNDCRAFT_CONTROL_PORT=(\d+)', log.read_text())
            if m:
                self.port = int(m.group(1))
                # Give llvmpipe/X11 its first visible frame before synthetic input.
                time.sleep(3)
                self.window = subprocess.check_output(['xdotool', 'search', '--onlyvisible', '--pid', str(self.process.pid)], env=self.env).decode().splitlines()[-1]
                subprocess.check_call(['xdotool', 'windowactivate', '--sync', self.window], env=self.env)
                return
            time.sleep(.2)
        raise RuntimeError('Control startup timed out')

    def rpc(self, method, params=None):
        self.serial += 1
        with socket.create_connection(('127.0.0.1', self.port), 30) as connection:
            channel = connection.makefile('rwb')
            channel.write((json.dumps({'id': self.serial, 'method': method, 'params': params or {}})+'\n').encode())
            channel.flush()
            response = json.loads(channel.readline().decode())
            assert response.get('ok'), response
            return response.get('result')

    def cmd(self, command, params=None):
        return self.rpc('engine.execute', {'command': command, 'params': params or {}})

    def click(self, x, y):
        subprocess.check_call(['xdotool', 'windowactivate', '--sync', self.window,
                               'mousemove', '--window', self.window, str(x), str(y), 'click', '1'], env=self.env)
        time.sleep(1)

    def key(self, key, **mods):
        key = {'Enter': 'Return', 'Escape': 'Escape'}.get(key, key.lower())
        if mods.get('cmd'):
            key = 'ctrl+'+key
        subprocess.check_call(['xdotool', 'windowactivate', '--sync', self.window, 'key', '--clearmodifiers', key], env=self.env)
        time.sleep(.6)

    def text(self, text):
        subprocess.check_call(['xdotool', 'type', '--clearmodifiers', '--delay', '5', text], env=self.env)
        time.sleep(.6)

    def shot(self, name):
        time.sleep(1)
        window = subprocess.check_output(['xdotool', 'search', '--onlyvisible', '--pid', str(self.process.pid)], env=self.env).decode().splitlines()[-1]
        subprocess.check_call(['import', '-window', window, str(self.base/name)], env=self.env)

    def native_path(self, path):
        self.click(622, 252)  # Browse in the visually checked 1500 x 650 PathPrompt.
        until = time.monotonic()+30
        while time.monotonic() < until:
            rows = subprocess.check_output(['ps', '-eo', 'pid,ppid,comm']).decode().splitlines()
            owned = [int(x[0]) for row in rows for x in [row.split()]
                     if len(x) == 3 and x[1] == str(self.process.pid) and x[2] == 'zenity']
            if owned:
                window = subprocess.run(['xdotool', 'search', '--onlyvisible', '--pid', str(owned[0])], env=self.env, stdout=subprocess.PIPE)
                if window.returncode == 0:
                    break
            time.sleep(.2)
        else:
            raise RuntimeError('Owned native chooser not observed')
        window = window.stdout.decode().splitlines()[-1]
        subprocess.check_call(['xdotool', 'windowactivate', '--sync', window, 'key', 'ctrl+l'], env=self.env)
        subprocess.check_call(['xdotool', 'type', '--clearmodifiers', '--delay', '2', str(path)], env=self.env)
        subprocess.check_call(['xdotool', 'key', 'Return'], env=self.env)
        time.sleep(1)
        self.key('Enter')

    def idle(self):
        time.sleep(4)
        def ticks():
            fields = Path('/proc/%d/stat' % self.process.pid).read_text().rsplit(')', 1)[1].split()
            return int(fields[11])+int(fields[12])
        before, start = ticks(), time.monotonic()
        time.sleep(10)
        cpu = 100*(ticks()-before)/os.sysconf('SC_CLK_TCK')/(time.monotonic()-start)
        status = Path('/proc/%d/status' % self.process.pid).read_text()
        rss = int(re.search(r'^VmRSS:\s+(\d+) kB', status, re.M).group(1))
        assert cpu <= 5 and rss <= 350*1024, (cpu, rss)
        return {'cpu_percent_one_logical_cpu': cpu, 'rss_kib': rss, 'seconds': 10}

    def close(self):
        if self.process and self.process.poll() is None:
            try:
                self.rpc('app.quit'); self.process.wait(timeout=5)
            except (OSError, AssertionError, subprocess.TimeoutExpired):
                self.process.terminate(); self.process.wait(timeout=10)
        if hasattr(self, 'stream'):
            self.stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--parent', type=Path, required=True)
    args = parser.parse_args()
    base = Path(tempfile.mkdtemp(prefix='gui-', dir=str(args.parent))).resolve()
    headless = max(args.parent.glob('headless-*/headless-result.json'), key=lambda p: p.stat().st_mtime)
    fixture = json.loads(headless.read_text()); assert fixture['passed']
    media = headless.parent
    app = App(args.binary.resolve(), base)
    result = {'passed': False, 'binary_sha256': hashlib.sha256(args.binary.read_bytes()).hexdigest(),
              'no_audio': True, 'fixture': str(base), 'checks': []}
    try:
        app.start(); time.sleep(4)
        assert app.rpc('ui.inspect')['window_size'] == [1500.0, 650.0]
        app.rpc('ui.menu.invoke', {'id': 'session.new'}); time.sleep(1)
        app.shot('new.png'); app.click(790, 211); app.key('A', cmd=True)
        app.text('VAIO GUI synthetic mix'); app.click(678, 305)
        state = app.rpc('session.inspect')
        assert state['name'] == 'VAIO GUI synthetic mix', state
        for label in ('a', 'b'):
            app.cmd('file.import_audio', {'path': str(media/('tone-'+label+'.wav')), 'at': 0})
        result['dirty_idle'] = app.idle()
        assert list((base/'profile/Autosave').glob('*/session.scraft'))
        app.rpc('ui.menu.invoke', {'id': 'session.save_as'}); time.sleep(1); app.shot('save.png')
        app.native_path(base/'native-saved'); time.sleep(1)
        saved = app.rpc('session.inspect', {'detail': 'full'})
        assert saved['path'].endswith('native-saved.scraft') and not saved['dirty'], saved
        result['checks'] += ['GUI text entry and two-track import', 'dirty idle and background autosave', 'native bare-name Save As']
        protected = base/'protected.scraft'; protected.write_bytes(b'original synthetic marker')
        app.rpc('ui.menu.invoke', {'id': 'session.save_as'}); time.sleep(1); app.click(790, 224)
        app.key('A', cmd=True); app.text(str(protected))
        app.key('Enter'); assert app.rpc('ui.inspect')['dialog'] == 'path'
        app.shot('overwrite.png'); app.key('Escape')
        assert protected.read_bytes() == b'original synthetic marker'
        result['checks'].append('existing session overwrite refused on Enter; cancelled')
        track = saved['tracks'][0]['id']; app.cmd('track.rename', {'track': track, 'name': 'Recovery verified tone'}); time.sleep(2)
        assert list((base/'profile/Autosave').glob('*/session.scraft'))
        app.process.kill(); app.process.wait(timeout=5); app.stream.close()
        app.start(); time.sleep(4); app.shot('recovery.png'); app.click(687, 285); time.sleep(1)
        recovered = app.rpc('session.inspect', {'detail': 'full'})
        assert len(recovered['tracks']) == 2 and recovered['tracks'][0]['name'] == 'Recovery verified tone', recovered
        app.cmd('session.save_as', {'path': str(base/'recovered.scraft')})
        app.cmd('file.bounce_mix', {'path': str(base/'recovered.wav'), 'start': 0, 'end': 96000, 'bit_depth': '32f', 'dither': False})
        result['checks'].append('actual unsaved recovery UI retains both tracks and edit; bounce succeeds')
        app.rpc('ui.menu.invoke', {'id': 'session.open'}); time.sleep(1); app.shot('open.png')
        app.native_path(base/'native-saved.scraft'); time.sleep(1)
        reopened = app.rpc('session.inspect', {'detail': 'full'})
        assert reopened['tracks'][0]['name'] == 'tone-a' and len(reopened['tracks']) == 2
        result['checks'].append('native Open restores saved content')
        app.rpc('ui.menu.invoke', {'id': 'session.save_as'}); time.sleep(1); app.shot('default-save.png')
        app.key('Enter'); time.sleep(1)
        default_saved = app.rpc('session.inspect', {'detail': 'full'})
        expected = base/'documents'/reopened['name']/(reopened['name']+'.scraft')
        assert default_saved['path'] == str(expected) and expected.is_file(), default_saved
        result['checks'].append('internal Save As uses the configured document folder')
        result['settled_idle'] = app.idle(); app.shot('final.png')
        assert app.rpc('ui.inspect')['audio_device'] is None
        result['passed'] = True
    except BaseException as error:
        result['error'] = repr(error)
        result['traceback'] = traceback.format_exc()
    finally:
        app.close(); (base/'gui-result.json').write_text(json.dumps(result, indent=2)+'\n')
        (args.parent/'gui-result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
