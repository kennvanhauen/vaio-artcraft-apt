#!/usr/bin/python3
"""Bounded output-only SoundCraft fixture; run under an outer 25-second timeout.

The child stays in the outer timeout's process group. No recording, user media,
GUI manipulation or persistent diagnostic watcher/configuration is involved.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def main():
    stage, media = Path(sys.argv[1]), Path(sys.argv[2])
    seconds = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    gain = float(sys.argv[4]) if len(sys.argv) > 4 else -12.0
    assert 2 <= seconds <= 30 and -24 <= gain <= 6
    assert str(stage).startswith('/tmp/vaio-soundcraft-') and media.is_file()
    binary = stage / 'vaio_output'
    status = Path('/proc/asound/card0/pcm0p/sub0/status')
    assert status.read_text().strip() == 'closed', 'Existing playback; defer test'
    env = dict(os.environ, XDG_RUNTIME_DIR='/run/user/1000')
    assert not subprocess.check_output(['pactl', 'list', 'short', 'sink-inputs'], env=env).strip()
    before = set(subprocess.check_output(['dmesg']).decode().splitlines())
    fault = re.compile(r'azx_get_response|no response from codec|CORB.*timeout|RIRB.*(error|timeout)|BUG:|Oops:', re.I)
    assert not [x for x in before if fault.search(x)], 'Existing kernel fault; defer playback'
    result = {'passed': False, 'seconds_requested': seconds, 'track_gain_db': gain, 'recorder_created': False}
    stdout = (stage / 'output-stdout.json').open('w')
    stderr = (stage / 'output-stderr.log').open('w')
    child = subprocess.Popen([str(binary), str(media), str(seconds), str(gain)], env=env, stdout=stdout, stderr=stderr)
    start, last_progress, last_kernel = time.monotonic(), time.monotonic(), time.monotonic()
    last_ptr, running, pointers, peak_rss, ticks = None, False, [], 0, 0
    try:
        while child.poll() is None:
            now = time.monotonic()
            raw = status.read_text()
            values = dict((k.strip(), v.strip()) for k, v in
                          (line.split(':', 1) for line in raw.splitlines() if ':' in line))
            if values.get('state') == 'RUNNING':
                if not running:
                    running, last_progress = True, now
                ptr = values.get('hw_ptr')
                if ptr != last_ptr:
                    last_ptr, last_progress = ptr, now
                    pointers.append(ptr)
                assert now - last_progress < 0.8, 'ALSA playback pointer stalled'
            try:
                stat = Path('/proc/' + str(child.pid) + '/stat').read_text().rsplit(')', 1)[1].split()
                ticks = int(stat[11]) + int(stat[12])
                proc_status = Path('/proc/' + str(child.pid) + '/status').read_text()
                match = re.search(r'^VmRSS:\s+(\d+) kB', proc_status, re.M)
                if match:
                    peak_rss = max(peak_rss, int(match.group(1)))
            except (IOError, OSError):
                pass
            if now - last_kernel >= 0.5:
                fresh = subprocess.check_output(['dmesg']).decode().splitlines()
                errors = [x for x in fresh if x not in before and fault.search(x)]
                assert not errors, errors
                last_kernel = now
            assert now - start < seconds + 5, 'Bounded playback deadline exceeded'
            time.sleep(0.1)
        child_elapsed = time.monotonic() - start
        assert child.returncode == 0, 'Playback check exit ' + str(child.returncode)
        stdout.close()
        detail = json.loads((stage / 'output-stdout.json').read_text())
        assert detail['passed'] and not detail['silent'] and not detail['recorder_created'], detail
        assert running and len(set(pointers)) > 20, 'No verified hardware progress'
        for attempt in range(50):
            if status.read_text().strip() == 'closed':
                break
            time.sleep(0.1)
        assert status.read_text().strip() == 'closed'
        errors = [x for x in subprocess.check_output(['dmesg']).decode().splitlines()
                  if x not in before and fault.search(x)]
        assert not errors, errors
        result.update(passed=True, detail=detail, distinct_hardware_pointers=len(set(pointers)),
                      playback_closed=True, new_kernel_faults=errors, peak_rss_kib=peak_rss,
                      child_runtime_seconds=round(child_elapsed, 3), child_cpu_ticks=ticks,
                      approximate_child_cpu_percent_one_logical_cpu=round(100 * ticks / os.sysconf('SC_CLK_TCK') / child_elapsed, 2),
                      measurement_context='Active synthetic playback; not an idle measurement')
    except BaseException as exc:
        result['error'] = repr(exc)
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=1)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=2)
        stdout.close()
        stderr.close()
        result['elapsed_seconds'] = round(time.monotonic() - start, 3)
        (stage / 'output-result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
