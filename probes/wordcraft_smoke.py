#!/usr/bin/env python3
"""Real-VAIO short-document smoke test. Synthetic files and an isolated profile.

Run: DISPLAY=:0 python3 wordcraft_smoke.py /tmp/vaio-wordcraft-test
Never logs the control-channel key, touches user documents, or starts audio.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

base = Path(sys.argv[1]).resolve()
base.mkdir(exist_ok=True, parents=True)
env = dict(os.environ, DISPLAY=':0', WORDCRAFT_NO_PREFS='1',
           WORDCRAFT_PROFILE_DIR=str(base / 'profile'),
           LD_LIBRARY_PATH=str(base / 'lib'))
cli = os.environ.get('VAIO_WORDCRAFT_CLI', str(base / 'bin/wordcraft-cli'))
binary = os.environ.get('VAIO_WORDCRAFT_BINARY', str(base / 'bin/wordcraft'))
original = base / 'synthetic.docx'
saved = base / 'typed.docx'
roundtrip = base / 'roundtrip.docx'
initial_text = 'VAIO compatibility test. This disposable document contains synthetic text only.'
typed_text = ' Typed through the WordCraft interface on the VAIO.'
results = {'commands': [], 'measurements': [],
           'binary': binary, 'cli': cli,
           'static_caret_enabled': bool(os.environ.get('WORDCRAFT_STATIC_CARET'))}

def run_cli(*arguments):
    at = time.monotonic()
    completed = subprocess.run([cli] + list(arguments), env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True, timeout=60)
    results['commands'].append({'cli': list(arguments), 'returncode': completed.returncode,
                                'seconds': round(time.monotonic()-at, 4),
                                'stdout': completed.stdout, 'stderr': completed.stderr})
    if completed.returncode:
        raise RuntimeError('CLI failed: ' + completed.stderr)
    return completed.stdout

def sample(pid):
    fields = Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()
    status = Path('/proc/%d/status' % pid).read_text()
    rss = next(int(line.split()[1]) for line in status.splitlines() if line.startswith('VmRSS:'))
    return int(fields[11])+int(fields[12]), rss

def measure(label, process, duration=5):
    cpu, rss = sample(process.pid)
    at = time.monotonic()
    time.sleep(duration)
    later_cpu, later_rss = sample(process.pid)
    elapsed = time.monotonic()-at
    results['measurements'].append({'phase': label, 'seconds': round(elapsed, 3),
        'process_cpu_percent_one_logical_cpu': round(100*(later_cpu-cpu)/os.sysconf('SC_CLK_TCK')/elapsed, 2),
        'rss_kib_start': rss, 'rss_kib_end': later_rss})

def docx_content(path):
    with zipfile.ZipFile(str(path)) as archive:
        document = ET.fromstring(archive.read('word/document.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    text = ''.join(node.text or '' for node in document.findall('.//w:t', ns))
    bold = []
    for run in document.findall('.//w:r', ns):
        if run.find('w:rPr/w:b', ns) is not None:
            bold.append(''.join(node.text or '' for node in run.findall('w:t', ns)))
    return {'text': text, 'bold_runs': bold}

process = None
transport = None
log = None
try:
    results['version'] = subprocess.check_output([binary, '--version'], env=env).decode().strip()
    run_cli('run', '--cmd', 'text.insert='+json.dumps({'text': initial_text}), '--save', str(original))
    log = (base / 'application.log').open('w')
    at = time.monotonic()
    process = subprocess.Popen([binary, '--control', '7981', str(original)],
                               env=env, stdout=log, stderr=log, stdin=subprocess.DEVNULL)
    key_path = base / 'profile/control-key.local-7981'
    deadline = time.monotonic()+60
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Application exited during startup: '+str(process.returncode))
        if key_path.exists():
            try:
                transport = socket.create_connection(('127.0.0.1', 7981), timeout=15)
                break
            except OSError:
                pass
        time.sleep(.25)
    if transport is None:
        raise RuntimeError('Control channel did not become ready within 60 seconds')
    results['control_ready_seconds'] = round(time.monotonic()-at, 4)
    channel = transport.makefile('rwb', buffering=0)
    key = key_path.read_text().strip()
    serial = 0

    def request(method, params=None):
        global serial
        serial += 1
        payload = {'id': serial, 'key': key, 'method': method, 'params': params or {}}
        at = time.monotonic()
        channel.write((json.dumps(payload)+'\n').encode())
        reply = json.loads(channel.readline().decode())
        results['commands'].append({'method': method, 'params': params or {},
                                    'seconds': round(time.monotonic()-at, 4), 'reply': reply})
        if not reply.get('ok'):
            raise RuntimeError(method+' failed: '+str(reply.get('error')))
        return reply.get('result')

    request('ui.resize', {'width': 1000, 'height': 650})
    time.sleep(1)
    results['initial_ui'] = request('ui.inspect')
    results['runtime_shared_libraries'] = sorted({line.split()[-1]
        for line in Path('/proc/%d/maps' % process.pid).read_text().splitlines()
        if '.so' in line and '/' in line.split()[-1]})
    time.sleep(1)
    measure('default_idle', process)
    results['default_idle_ui'] = request('ui.inspect')
    request('engine.execute', {'command': 'ui.animations', 'params': {'value': 'off'}})
    request('engine.execute', {'command': 'ui.caretAnimation', 'params': {'value': False}})
    time.sleep(1)
    measure('reduced_animation_idle', process)
    results['reduced_idle_ui'] = request('ui.inspect')
    request('engine.execute', {'command': 'caret.docEnd', 'params': {}})
    request('ui.focus')
    request('engine.execute', {'command': 'format.bold', 'params': {}})
    request('ui.text', {'text': typed_text})
    time.sleep(1)
    request('engine.execute', {'command': 'file.save', 'params': {'path': str(saved)}})
    results['edited_content'] = docx_content(saved)
    if results['edited_content']['text'] != initial_text+typed_text:
        raise RuntimeError('Typed text was not saved as expected')
    if typed_text not in ''.join(results['edited_content']['bold_runs']):
        raise RuntimeError('Bold formatting was not saved')
    request('ui.screenshot', {'path': str(base / 'wordcraft-ui.png')})
    results['final_ui'] = request('ui.inspect')
    request('engine.execute', {'command': 'file.open', 'params': {'path': str(saved)}})
    results['reopened_document'] = request('document.inspect')
    run_cli('run', '--file', str(saved), '--save', str(roundtrip))
    results['roundtrip_content'] = docx_content(roundtrip)
    if results['roundtrip_content'] != results['edited_content']:
        raise RuntimeError('DOCX text/formatting changed on round trip')
    results['passed'] = True
    request('app.quit')
    process.wait(timeout=15)
    results['application_returncode'] = process.returncode
except Exception as error:
    results['passed'] = False
    results['error'] = str(error)
finally:
    if transport:
        transport.close()
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    if log:
        log.close()
    (base / 'smoke-result.json').write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps({key: value for key, value in results.items()
                      if key in ('passed', 'error', 'version', 'control_ready_seconds', 'measurements')}, indent=2))
sys.exit(0 if results.get('passed') else 1)
