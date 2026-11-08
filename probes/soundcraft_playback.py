#!/usr/bin/python3
"""Bounded real GUI playback of synthetic media, with no recording or user files."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

from soundcraft_gui import App
from soundcraft_headless import fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--parent', type=Path, required=True)
    args = parser.parse_args()
    base = Path(tempfile.mkdtemp(prefix='playback-', dir=str(args.parent)))
    status = Path('/proc/asound/card0/pcm0p/sub0/status')
    capture = Path('/proc/asound/card0/pcm0c/sub0/status')
    fault = re.compile(r'azx_get_response|no response from codec|CORB.*timeout|RIRB.*(error|timeout)|BUG:|Oops:', re.I)
    kernel = lambda: set(subprocess.check_output(['dmesg']).decode().splitlines())
    result = {'passed': False, 'fixture': str(base), 'recording_armed': False,
              'measurement_context': 'Active synthetic GUI playback; not idle'}
    app = None
    try:
        assert status.read_text().strip() == 'closed', 'Existing playback; defer test'
        assert capture.read_text().strip() == 'closed', 'Existing capture; defer test'
        assert not subprocess.check_output(['pactl', 'list', 'short', 'sink-inputs']).strip()
        sinks=subprocess.check_output(['pactl','list','sinks']).decode()
        assert 'Mute: no' in sinks, 'Output is muted; no audible test can be claimed'
        result['output_unmuted']=True
        before = kernel()
        assert not [line for line in before if fault.search(line)], 'Existing kernel audio fault'
        fixture(base/'tone.wav', 48000, 480000, (440, 660), 0.03)
        app = App(args.binary, base)
        app.start(audio=True)
        ui = app.rpc('ui.inspect')
        assert ui['audio_device'], ui
        app.cmd('session.new', {'name': 'Synthetic playback check', 'sample_rate': 48000})
        app.cmd('file.import_audio', {'path': str(base/'tone.wav'), 'at': 0})
        session = app.rpc('session.inspect', {'detail': 'full'})
        assert len(session['tracks']) == 1
        app.cmd('mix.volume', {'track': session['tracks'][0]['id'], 'db': -6})
        app.cmd('transport.play', {'from': 0})
        start = last_progress = time.monotonic()
        pointers = []
        while time.monotonic() - start < 8:
            assert app.process.poll() is None, 'GUI exited during playback'
            raw = status.read_text()
            values = dict((k.strip(), v.strip()) for k, v in
                          (line.split(':', 1) for line in raw.splitlines() if ':' in line))
            if values.get('state') == 'RUNNING':
                pointer = values.get('hw_ptr')
                if not pointers or pointer != pointers[-1]:
                    pointers.append(pointer)
                    last_progress = time.monotonic()
            assert time.monotonic() - last_progress < 1, 'Audio hardware pointer stalled'
            assert capture.read_text().strip() == 'closed', 'Capture unexpectedly opened'
            assert not [line for line in kernel() - before if fault.search(line)]
            time.sleep(.15)
        assert len(set(pointers)) > 20, 'Insufficient audio hardware progress'
        running = app.rpc('ui.inspect')
        assert running['playing'] and running['position'] > 0, running
        app.cmd('transport.stop')
        time.sleep(1)
        assert not app.rpc('ui.inspect')['playing'], 'Transport did not stop'
        result.update(audio_device=ui['audio_device'], seconds=8,
                      position=running['position'], distinct_hardware_pointers=len(set(pointers)),
                      transport_stopped=True, capture_closed=True)
        app.close()
        app = None
        until = time.monotonic() + 8
        while time.monotonic() < until and status.read_text().strip() != 'closed':
            time.sleep(.2)
        assert status.read_text().strip() == 'closed', 'Playback device did not close'
        assert not [line for line in kernel() - before if fault.search(line)]
        result.update(passed=True, playback_closed=True, new_kernel_faults=[])
    except BaseException as error:
        import traceback
        result.update(error=repr(error), traceback=traceback.format_exc())
    finally:
        if app:
            app.close()
        (args.parent/'playback-result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
