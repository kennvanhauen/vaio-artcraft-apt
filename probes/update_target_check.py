#!/usr/bin/env python3
"""Python 3.5-compatible, rootless candidate acceptance on the actual VAIO.

Only extracted candidate binaries and synthetic fixtures are used. No APT install,
network change, session termination or reboot occurs. All test process groups are
owned by this runner. Leave unrelated application windows/processes alone.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

BASE = Path(__file__).resolve().parent


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def output(args):
    return subprocess.check_output(args).decode().strip()


def fixture_pdf(path):
    # Original three-page ASCII fixture; no document/package dependencies.
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [4 0 R 6 0 R 8 0 R] /Count 3 >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for n in range(1, 4):
        content = ('BT /F1 18 Tf 72 720 Td (test page %d) Tj ET' % n).encode()
        objects += [('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
                     '/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>' % (n*2+3)).encode(),
                    ('<< /Length %d >>\nstream\n' % len(content)).encode()+content+b'\nendstream']
    data = b'%PDF-1.4\n'; offsets = [0]
    for index, value in enumerate(objects, 1):
        offsets.append(len(data)); data += ('%d 0 obj\n' % index).encode()+value+b'\nendobj\n'
    at = len(data)
    data += ('xref\n0 %d\n0000000000 65535 f \n' % len(offsets)).encode()
    data += b''.join(('%010d 00000 n \n' % pos).encode() for pos in offsets[1:])
    data += ('trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(offsets), at)).encode()
    path.write_bytes(data)


def processes():
    result = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            cmd = (p/'cmdline').read_bytes().split(b'\0')[0]
            if str(BASE).encode() in cmd:
                result.append(int(p.name))
        except OSError:
            pass
    return result


def bounded(script, arguments, env, log):
    with log.open('w') as stream:
        process = subprocess.Popen(['python3', str(script)]+arguments, env=env,
                                   stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=480)
            assert code == 0, script.name+' failed; inspect '+str(log)
        finally:
            # These children belong to a new session created specifically for this test.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            process.wait(timeout=10)


def runtime():
    return {'kernel': output(['uname', '-r']), 'architecture': output(['uname', '-m']),
            'memory': output(['free', '-m']),
            'temperatures_millicelsius': [int(p.read_text()) for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')],
            'thermal_throttle_counts': {str(p): int(p.read_text()) for p in Path('/sys/devices/system/cpu').glob('cpu*/thermal_throttle/core_throttle_count')}}


def idle_metrics(data):
    if 'settled_idle' in data:
        sample = data['settled_idle']
        return sample['cpu_percent_one_logical_cpu'], sample['rss_kib']
    if 'settled_idle_cpu_percent_one_logical_cpu' in data:
        return data['settled_idle_cpu_percent_one_logical_cpu'], data['rss_kib']
    if 'measurements' in data:
        sample = data['measurements'][-1]
        return sample['process_cpu_percent_one_logical_cpu'], sample['rss_kib_end']
    return data['idle_cpu_percent_one_logical_cpu'], data['rss_kib']


def main():
    state = json.loads((BASE/'candidate.json').read_text())
    app, package = state['app'], state['package']
    result = {'passed': False, 'package_sha256': digest(BASE/'candidate.deb'),
              'runner_sha256': digest(Path(__file__)), 'steps': []}
    try:
        assert result['package_sha256'] == state['package_sha256'], 'Package transfer hash mismatch'
        result['before'] = runtime()
        assert result['before']['architecture'] in ('i386', 'i486', 'i586', 'i686')
        assert '16.04' in Path('/etc/lsb-release').read_text(), 'Wrong target OS'
        assert 'Atom' in Path('/proc/cpuinfo').read_text(), 'Wrong target CPU'
        assert all(t < 75000 for t in result['before']['temperatures_millicelsius']), 'Let machine cool before tests'
        ports = [7981, 7986, 7987, 7988, 7991, 7992, 7993, 7994, 7995]
        listeners = output(['ss', '-lnt'])
        assert not any(re.search(r':%d\s' % p, listeners) for p in ports), 'An unrelated control listener already uses a test port'
        control = output(['dpkg-deb', '-f', str(BASE/'candidate.deb'), 'Package', 'Version', 'Architecture'])
        assert 'Package: '+package in control and 'Version: '+state['version'] in control and 'Architecture: i386' in control
        installed = output(['dpkg-query', '-W', '-f=${Version}', package])
        result['installed_version'] = installed
        result['archive_version_newer'] = subprocess.call(['dpkg', '--compare-versions', state['version'], 'gt', state['baseline']['version']]) == 0
        result['version_newer'] = subprocess.call(['dpkg', '--compare-versions', state['version'], 'gt', installed]) == 0
        extracted = BASE/'extracted'
        subprocess.check_call(['dpkg-deb', '-x', str(BASE/'candidate.deb'), str(extracted)])
        manifest = json.loads((extracted/('usr/share/doc/'+package+'/build.json')).read_text())
        assert manifest['package_version'] == state['version']
        assert manifest.get('source_revision', manifest.get('upstream_revision')) == state['revision']
        binaries = manifest['binary_sha256']
        if isinstance(binaries, str):
            binaries = {'launcher': binaries}
        for name, expected in binaries.items():
            path = extracted/('usr/lib/'+package+'/bin/'+name)
            assert digest(path) == expected
            elf = path.read_bytes()[:20]
            assert elf[:6] == b'\x7fELF\x01\x01' and elf[18:20] == b'\x03\x00'
            # ldd on the actual Xenial machine detects missing/too-new symbol versions.
            linked = subprocess.check_output(['ldd', str(path)], env=dict(os.environ, LD_LIBRARY_PATH=str(extracted/('usr/lib/'+package+'/lib'))), stderr=subprocess.STDOUT).decode()
            assert 'not found' not in linked and 'version `' not in linked, linked
        result['steps'].append('Xenial dpkg metadata, ELF, manifest hashes and native dependency loading')
        work = BASE/'work'; work.mkdir()
        prefixes = ['/tmp/vaio-wordcraft-test', '/tmp/vaio-everyday', '/tmp/vaio-deckcraft-test',
                    '/tmp/vaio-vectorcraft-test', '/tmp/vaio-designcraft-test', '/tmp/vaio-figcraft-test', '/tmp/vaio-cadcraft-test']
        rewritten = BASE/'adapted-probes'; rewritten.mkdir()
        for probe in (BASE/'probes').glob('*.py'):
            text = probe.read_text()
            for prefix in prefixes:
                text = text.replace(prefix, str(work/Path(prefix).name))
            if app == 'launcher':
                text = text.replace('/usr/bin/vaio-app-launcher', str(BASE/'launcher-wrapper'))
            (rewritten/probe.name).write_text(text)
        env = dict(os.environ, DISPLAY=':0', DECKCRAFT_NO_AUDIO='1', WORDCRAFT_STATIC_CARET='1',
                   DECKCRAFT_STATIC_CARET='1', DESIGNCRAFT_STATIC_CARET='1', FIGCRAFT_STATIC_CARET='1',
                   PDFCRAFT_RENDERER='gl', PDFCRAFT_SYSTEM_FONTS='0', XDG_CONFIG_HOME=str(work/'global-config'),
                   XDG_DATA_HOME=str(work/'global-data'), XDG_CACHE_HOME=str(work/'global-cache'))
        # Wrappers always force this candidate's XCB even if a historic probe sets LD_LIBRARY_PATH.
        compatibility = work/('vaio-everyday' if app in ('gridcraft', 'pdfcraft') else 'vaio-'+app+'-test')
        compatibility.mkdir(parents=True)
        short = {'wordcraft': 'WORDCRAFT', 'gridcraft': 'GRID', 'pdfcraft': 'PDF', 'deckcraft': 'DECK',
                 'vectorcraft': 'VECTOR', 'designcraft': 'DESIGN', 'figcraft': 'FIG', 'cadcraft': 'CAD'}.get(app)
        wrappers = {}
        for name in binaries:
            path = BASE/'launcher-wrapper' if app == 'launcher' else compatibility/name
            path.write_text('#!/bin/sh\nexport LD_LIBRARY_PATH="'+str(extracted/('usr/lib/'+package+'/lib'))+'${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\nexec "'+str(extracted/('usr/lib/'+package+'/bin/'+name))+'" "$@"\n')
            path.chmod(0o755); wrappers[name] = path
            if short:
                env['VAIO_'+short+('_CLI' if name.endswith('-cli') else '_BINARY')] = str(path)
        if app in ('wordcraft', 'gridcraft', 'pdfcraft', 'deckcraft'):
            headless = dict(env)
            for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY'):
                headless.pop(key, None)
            help_run = subprocess.run([str(wrappers[app+'-cli']), '--help'], env=headless,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            assert help_run.returncode == 0 and help_run.stdout, 'No-display CLI startup failed'
            result['steps'].append('CLI startup without display variables')
        subprocess.call(['xscreensaver-command', '-deactivate'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if app == 'wordcraft':
            steps = [('wordcraft_smoke.py', [str(compatibility)], compatibility/'smoke-result.json'),
                     ('native_dialog_test.py', ['--bare'], work/'vaio-everyday/native-bare-result.json')]
            env['VAIO_TEST_BINARY'] = str(wrappers['wordcraft'])
            env['VAIO_TEST_EXPECTED_TEXT'] = 'Typed through the WordCraft interface on the VAIO.'
        elif app in ('gridcraft', 'pdfcraft', 'deckcraft'):
            steps = [(app+'_smoke.py', [], compatibility/('result.json' if app == 'deckcraft' else app+'-test/result.json')),
                     (app+'_native_dialogs.py', [], compatibility/('native-dialogs/result.json' if app == 'deckcraft' else app+'-dialogs/result.json'))]
            if app == 'pdfcraft':
                fixture_pdf(compatibility/'allowed-pdf-test.pdf')
        elif app == 'soundcraft':
            steps = [('soundcraft_headless.py', ['--cli', str(wrappers['soundcraft-cli']), '--parent', str(compatibility)], compatibility/'headless-result.json'),
                     ('soundcraft_gui.py', ['--binary', str(wrappers['soundcraft']), '--parent', str(compatibility)], compatibility/'gui-result.json')]
        elif app == 'launcher':
            steps = [('launcher_eight_open.py', [], work/'vaio-cadcraft-test/launcher-eight-open/result.json')]
        else:
            steps = [(app+'_headless.py', [], compatibility/'headless-result.json'),
                     (app+'_gui.py', [], compatibility/'gui-result.json'),
                     (app+'_native_dialogs.py', [], compatibility/'native-dialogs/result.json')]
        if app == 'wordcraft':
            env['VAIO_WORDCRAFT_CLI'] = str(wrappers['wordcraft-cli'])
        measurements = []
        for script, arguments, filename in steps:
            if script == 'native_dialog_test.py':
                everyday = work/'vaio-everyday'; everyday.mkdir(exist_ok=True)
                for name in ('report.docx', 'edited.docx'):
                    shutil.copy2(str(compatibility/'typed.docx'), str(everyday/name))
            bounded(rewritten/script, arguments, env, BASE/(script+'.log'))
            data = json.loads(filename.read_text())
            assert data.get('passed') is True, data
            result['steps'].append(script)
            if script.endswith('_gui.py') or script.endswith('_smoke.py') or script == 'launcher_eight_open.py':
                cpu, rss = idle_metrics(data)
                measurements.append({'probe': script, 'idle_cpu_percent': cpu, 'rss_kib': rss})
                assert cpu <= 5.0 and rss <= 350*1024, 'Idle CPU/RAM budget exceeded'
        result['measurements'] = measurements
        result['after'] = runtime()
        assert result['after']['thermal_throttle_counts'] == result['before']['thermal_throttle_counts'], 'Throttle counter increased'
        assert all(t < 80000 for t in result['after']['temperatures_millicelsius']), 'Temperature budget exceeded'
        # No candidate process or listener should survive successful checks.
        result['leftover_candidate_processes'] = [p for p in processes() if p != os.getpid()]
        assert not result['leftover_candidate_processes']
        listeners = output(['ss', '-lnt'])
        assert not any(re.search(r':%d\s' % p, listeners) for p in ports)
        result['passed'] = True
    except Exception as error:
        result['error'] = repr(error)
    finally:
        (BASE/'target-result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
