#!/usr/bin/env python3
"""Mac coordinator for isolated ArtCraft updates. No unattended publication/install."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'maintenance/upstreams.json'
WORK = ROOT/'.build/updates'


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n')
    temporary.replace(path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def run(args, cwd=None, env=None, log=None, timeout=7200):
    if log:
        with Path(log).open('w') as output:
            subprocess.run([str(a) for a in args], cwd=cwd, env=env, check=True,
                           stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        return ''
    return subprocess.check_output([str(a) for a in args], cwd=cwd, env=env,
                                   text=True, stderr=subprocess.PIPE, timeout=timeout).strip()


@contextmanager
def locked():
    WORK.mkdir(parents=True, exist_ok=True)
    with (WORK/'coordinator.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another update coordinator is running')
        yield


def config():
    return read(CONFIG)


def source_name(app):
    return 'craft-launcher' if app == 'launcher' else app


def check(apps):
    report = {'observed_at': datetime.now(timezone.utc).isoformat(), 'apps': {}}
    for app in apps:
        spec = config()['apps'][app]
        result = {'pinned': spec['revision'], 'published_version': spec['version']}
        try:
            refs = run(['git', 'ls-remote', 'https://github.com/'+spec['repo']+'.git',
                        'HEAD', 'refs/tags/*'], timeout=90).splitlines()
            head = next(line.split()[0] for line in refs if line.endswith('\tHEAD'))
            result.update(head=head, changed=head != spec['revision'],
                          tags=[line.split()[1][10:] for line in refs if '\trefs/tags/' in line][-30:])
            print(app+': '+('upstream changes' if result['changed'] else 'at published source'), flush=True)
        except (subprocess.SubprocessError, StopIteration) as error:
            result['error'] = str(error)
            print(app+': check failed', flush=True)
        report['apps'][app] = result
    write(WORK/'upstream-report.json', report)
    return 1 if any('error' in r for r in report['apps'].values()) else 0


def candidate(path):
    path = Path(path).resolve()
    if not path.is_relative_to(WORK.resolve()) or not (path/'candidate.json').is_file():
        raise RuntimeError('Expected a candidate directory under .build/updates')
    return path, read(path/'candidate.json')


def snapshot(root):
    """Bind evidence to source, port, recipes and lockfile, excluding build products."""
    paths = [p for top in ('probes', 'ports') for p in (root/top).rglob('*')
             if p.is_file() and '__pycache__' not in p.parts]
    for tree in (root/'.build').glob('*-port') if (root/'.build').exists() else []:
        paths += [p for p in tree.rglob('*') if p.is_file() and 'target' not in p.relative_to(tree).parts and '.git' not in p.parts]
    state = read(root/'candidate.json')
    source = root/'upstream'/source_name(state.get('app', ''))
    if source.is_dir():
        paths += [p for p in source.rglob('*') if p.is_file() and '.git' not in p.relative_to(source).parts]
    if (root/'.build').exists():
        paths += list((root/'.build').glob('*fonts-verified.json'))
    paths += [root/'candidate.json']
    return {str(p.relative_to(root)): sha(p) for p in sorted(paths)}


def untar_git(source, revision, destination):
    destination.mkdir(parents=True)
    data = subprocess.check_output(['git', '-C', str(source), 'archive', revision])
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(destination, filter='data')


def apply_port_patch(tree, filename):
    # The workspace may itself be a Git checkout. Apply to this archive tree,
    # never discover/mutate an enclosing project's worktree or index.
    env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(tree.parent.resolve()))
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
        env.pop(name, None)
    run(['git', 'apply', '--check', filename], cwd=tree, env=env)
    run(['git', 'apply', filename], cwd=tree, env=env)


def lock_overlay(base_lock, port_lock, main_patch):
    """Apply VAIO dependency edges to the NEW upstream lock, never replace it."""
    if '+++ b/Cargo.lock' in main_patch:
        return ''  # Already applied by the main port patch.
    return ''.join(difflib.unified_diff(base_lock.splitlines(True), port_lock.splitlines(True),
                                        fromfile='a/Cargo.lock', tofile='b/Cargo.lock'))


def prepare(app, ref, version):
    spec = config()['apps'][app]
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}~vaio[1-9][0-9]*', version):
        raise RuntimeError('Use an explicit version such as 0.9.1~vaio1')
    if ref.startswith('-') or not re.fullmatch(r'[A-Za-z0-9_./-]+', ref):
        raise RuntimeError('Invalid source reference')
    cache = WORK/'sources'/app
    cache.parent.mkdir(exist_ok=True)
    if not cache.exists():
        run(['git', 'clone', '--mirror', 'https://github.com/'+spec['repo']+'.git', cache], timeout=300)
    else:
        run(['git', '-C', cache, 'fetch', '--prune', 'origin'], timeout=300)
    revision = run(['git', '-C', cache, 'rev-parse', '--verify', ref+'^{commit}'])
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    root = WORK/(app+'-'+stamp)
    root.mkdir()
    state = dict(app=app, revision=revision, version=version, package=spec['package'],
                 baseline=spec, status='preparing', schema=1)
    write(root/'candidate.json', state)
    try:
        for name in ('probes', 'ports'):
            shutil.copytree(ROOT/name, root/name, ignore=shutil.ignore_patterns('__pycache__'))
        (root/'.build').mkdir()
        (root/'dist').mkdir()
        (root/'upstream').mkdir()
        source = root/'upstream'/source_name(app)
        run(['git', 'clone', '--shared', '--no-checkout', cache, source])
        run(['git', '-C', source, 'checkout', '--detach', revision])
        tree = root/'.build'/(app+'-port')
        untar_git(source, revision, tree)
        # git apply refuses failed hunks; no fuzzy patching or edits to working ports.
        apply_port_patch(tree, root/'ports'/(app+'-xenial.patch'))
        lock = root/'ports'/(app+'-vaio.Cargo.lock')
        if lock.exists():
            base_revision = spec.get('port_base_revision', spec['revision'])
            base_lock = run(['git', '-C', cache, 'show', base_revision+':Cargo.lock'])+'\n'
            overlay = lock_overlay(base_lock, lock.read_text(), (root/'ports'/(app+'-xenial.patch')).read_text())
            if overlay:
                lock_patch = root/'lock-overlay.patch'; lock_patch.write_text(overlay)
                apply_port_patch(tree, lock_patch)
        if app == 'launcher':
            shutil.copytree(root/'ports/launcher-vaio', tree/'apps/artcraft-launcher-vaio')
            shutil.copy2(root/'ports/launcher-vaio/launcher.svg', tree/'assets/vaio-launcher.svg')
        # Share tools and immutable auxiliary inputs; targets/outputs stay isolated.
        inputs = ['cargo', 'rustup', 'zig-aarch64-macos-0.14.1', 'sysroot',
                  'private-lib', 'libxcb-1.17.0', 'pdfcraft-models']
        inputs += [p.name for p in (ROOT/'.build').glob('*fonts*')]
        for name in inputs:
            src = ROOT/'.build'/name
            if src.exists():
                if src.is_dir():
                    (root/'.build'/name).symlink_to(src, target_is_directory=True)
                else:
                    shutil.copy2(src, root/'.build'/name)
        if (ROOT/'upstream/craft-fonts').exists():
            (root/'upstream/craft-fonts').symlink_to(ROOT/'upstream/craft-fonts', target_is_directory=True)
        instructions = []
        for p in sorted(source.rglob('AGENTS.md')):
            instructions.append('## '+str(p.relative_to(source))+'\n\n'+p.read_text())
        (root/'UPSTREAM-INSTRUCTIONS.md').write_text('\n\n'.join(instructions))
        workspace = tomllib.loads((tree/'Cargo.toml').read_text())
        declared = workspace.get('workspace', {}).get('package', {}).get('version')
        if declared and version.split('~', 1)[0] != declared:
            raise RuntimeError('Debian upstream version must match Cargo workspace version '+declared)
        state.pop('error', None)
        state.update(status='prepared', upstream_version=declared)
    except Exception as error:
        state.update(status='prepare-failed', error=str(error))
        raise
    finally:
        write(root/'candidate.json', state)
        print(root)
    return root


def build(path):
    root, state = candidate(path)
    if (root/'publication.json').exists():
        raise RuntimeError('Published candidates cannot be rebuilt; prepare a new version')
    if state['status'] not in ('prepared', 'build-failed', 'built'):
        raise RuntimeError('Build requires a prepared candidate')
    # Rebuilding a local candidate must never preserve acceptance for its old inputs.
    invalidate_acceptance(root)
    app = state['app']
    env = dict(os.environ, VAIO_PACKAGE_SPEC=str(root/'candidate.json'), RUSTUP_TOOLCHAIN='1.95.0')
    try:
        compiler = root/'.build/rustup/toolchains/1.95.0-aarch64-apple-darwin/bin/rustc'
        if not run([compiler, '--version']).startswith('rustc 1.95.0 '):
            raise RuntimeError('Expected the installed project Rust 1.95.0 toolchain')
        if run([root/'.build/zig-aarch64-macos-0.14.1/zig', 'version']) != '0.14.1':
            raise RuntimeError('Expected the project Zig 0.14.1 toolchain')
        if app in ('deckcraft', 'vectorcraft', 'designcraft', 'figcraft', 'cadcraft'):
            run(['python3', 'probes/verify-'+app+'-fonts.py'], cwd=root, log=root/'fonts.log')
        # Run the unchanged cross recipes against this candidate's isolated root.
        commands = []
        if app in ('gridcraft', 'pdfcraft'):
            commands = [(['sh', 'probes/build-office-app.sh', app, '--locked'], {})]
        elif app == 'vectorcraft':
            commands = [(['sh', 'probes/build-vectorcraft.sh', '--locked'], {}),
                        (['sh', 'probes/build-vectorcraft.sh', '--locked', '-p', 'vectorcraft',
                          '--no-default-features', '--features', 'vaio'], {})]
        elif app in ('designcraft', 'figcraft', 'cadcraft', 'soundcraft'):
            commands = [(['sh', 'probes/build-'+app+'.sh', '--locked'], {app.upper()+'_BUILD': kind})
                        for kind in ('cli', 'gui')]
        else:
            commands = [(['sh', 'probes/build-'+app+'.sh']+([] if app == 'wordcraft' else ['--locked']), {})]
        for index, (args, extra) in enumerate(commands):
            print('Building '+app+' step '+str(index+1), flush=True)
            run(args, cwd=root, env=dict(env, **extra), log=root/('build-'+str(index)+'.log'))
        if app == 'wordcraft':
            target = root/'.build/test-runtime/bin'
            target.mkdir(parents=True, exist_ok=True)
            for name in ('wordcraft', 'wordcraft-cli'):
                shutil.copy2(root/'.build/wordcraft-target/i686-unknown-linux-gnu/release'/name, target/name)
            package_command = ['python3', 'probes/build_deb.py']
        elif app == 'launcher':
            package_command = ['python3', 'probes/build_launcher_deb.py']
        else:
            package_command = ['python3', 'probes/build_office_deb.py', app]
        run(package_command, cwd=root, env=env, log=root/'package.log')
        package = root/'dist'/(state['package']+'_'+state['version']+'_i386.deb')
        state.pop('error', None)
        state.update(status='built', package_sha256=sha(package), package_file=str(package.relative_to(root)))
        write(root/'candidate.json', state)
        write(root/'build-inputs.json', snapshot(root))
        print('Built '+str(package))
    except Exception as error:
        state.update(status='build-failed', error=str(error))
        write(root/'candidate.json', state)
        raise


def unchanged(root, state):
    package = root/state['package_file']
    if sha(package) != state['package_sha256'] or snapshot(root) != read(root/'build-inputs.json'):
        raise RuntimeError('Candidate changed since build; create/rebuild a candidate before verification')
    return package


def invalidate_acceptance(root):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    for name in ('host-result.json', 'target-result.json'):
        path = root/name
        if path.exists():
            history = root/'acceptance-history'/stamp
            history.mkdir(parents=True, exist_ok=True)
            path.replace(history/name)


def host_git_environment(root, state, tree, env):
    # Asset checks need the real tracked-file inventory even though the port is an
    # archive tree. Use a private index and upstream objects, never an enclosing repo.
    source = root/'upstream'/source_name(state['app'])
    env = dict(env, GIT_DIR=str(source/'.git'), GIT_WORK_TREE=str(tree),
               GIT_INDEX_FILE=str(root/'host-source.index'))
    run(['git', 'read-tree', state['revision']], cwd=tree, env=env)
    return env


def host_check(path):
    root, state = candidate(path)
    unchanged(root, state)
    app = state['app']
    tree = root/'.build'/(app+'-port')
    env = dict(os.environ, CARGO_HOME=str(root/'.build/cargo'), RUSTUP_HOME=str(root/'.build/rustup'), RUSTUP_TOOLCHAIN='1.95.0', CARGO_TARGET_DIR=str(root/'.build/host-target'))
    env['PATH'] = str(root/'.build/cargo/bin')+':'+env['PATH']
    env = host_git_environment(root, state, tree, env)
    result = {'passed': False, 'scope': 'workspace host tests excluding xtask and GPU UI crate; serial test execution'}
    try:
        ui_package = tomllib.loads((tree/'crates/ui-egui/Cargo.toml').read_text())['package']['name']
        run(['cargo', 'test', '--locked', '--workspace', '--exclude', 'xtask', '--exclude', ui_package,
             '--', '--test-threads=1'], cwd=tree, env=env, log=root/'host-tests.log')
        if app != 'launcher':
            for gate in ('assets', 'layers'):
                run(['cargo', 'run', '--locked', '-p', 'xtask', '--', gate], cwd=tree, env=env, log=root/('host-'+gate+'.log'))
        else:
            run(['python3', 'probes/test_apt_helper.py'], cwd=root, log=root/'host-helper.log')
        result['passed'] = True
    finally:
        result['package_sha256'] = state['package_sha256']
        write(root/'host-result.json', result)


def ssh_args(args, tool='ssh'):
    options = ['-o', 'BatchMode=yes', '-o', 'UpdateHostKeys=no', '-o', 'ConnectTimeout=8',
               '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2']
    if args.identity:
        options += ['-i', str(Path(args.identity).expanduser())]
    if not re.fullmatch(r'[A-Za-z0-9_.@-]+', args.ssh) or args.ssh.startswith('-'):
        raise RuntimeError('Invalid SSH host/alias')
    return [tool]+options


def remote_directory(root):
    name = root.name.lower()
    if not re.fullmatch(r'[a-z0-9-]+', name):
        raise RuntimeError('Invalid candidate directory name for remote transport')
    # Native-dialog probes type paths using unshifted XTEST keys.
    return '/tmp/vaio-update-'+name


def verify(path, args):
    root, state = candidate(path)
    package = unchanged(root, state)
    runner = root/'probes/update_target_check.py'
    if sha(runner) != sha(ROOT/'probes/update_target_check.py'):
        raise RuntimeError('Target runner changed since preparation; prepare a fresh candidate')
    attempt = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt = root/'target-result.json'
    if receipt.exists():
        history = root/'target-history'; history.mkdir(exist_ok=True)
        shutil.copy2(receipt, history/(attempt+'.json'))
    write(receipt, {'passed': False, 'package_sha256': state['package_sha256'],
                    'error': 'Verification incomplete', 'attempt': attempt})
    remote = remote_directory(root)+'-'+attempt.lower()
    ssh = ssh_args(args)+[args.ssh]
    scp = ssh_args(args, 'scp')
    # The remote runner is Python 3.5-compatible and extracts, never installs.
    run(ssh+['umask 077; mkdir '+remote], timeout=30)
    bundle = root/'verification.tar.gz'
    with tarfile.open(bundle, 'w:gz') as archive:
        archive.add(package, arcname='candidate.deb')
        archive.add(root/'candidate.json', arcname='candidate.json')
        archive.add(runner, arcname='runner.py')
        for p in (root/'probes').glob('*.py'):
            archive.add(p, arcname='probes/'+p.name)
    run(scp+[bundle, args.ssh+':'+remote+'/verification.tar.gz'], timeout=120)
    try:
        print('Running isolated tests on VAIO; package is not installed', flush=True)
        run(ssh+['cd '+remote+' && tar -xzf verification.tar.gz && python3 runner.py'],
            log=root/'target.log', timeout=1800)
    finally:
        # Result files can contain diagnostics; never automatically copy them public.
        run(scp+[args.ssh+':'+remote+'/target-result.json', root/'target-result.json'], timeout=60)
    result = read(root/'target-result.json')
    if not result.get('passed') or result.get('package_sha256') != state['package_sha256']:
        raise RuntimeError('VAIO check failed; inspect target.log and target-result.json')
    print('VAIO checks passed')


def rehearse(app, args):
    """Exercise transport/extraction/acceptance using a signed, already published package."""
    spec = config()['apps'][app]
    public = ROOT/'.build/apt-public'
    run(['gpgv', '--keyring', public/'vaio-artcraft-archive-keyring.gpg', public/'dists/xenial/InRelease'])
    # The index must be one of the exact SHA256 entries covered by Release/InRelease.
    release = (public/'dists/xenial/InRelease').read_text()
    index = public/'dists/xenial/main/binary-i386/Packages'
    if not re.search(r'^ '+sha(index)+r' '+str(index.stat().st_size)+r' main/binary-i386/Packages$', release, re.M):
        raise RuntimeError('Signed index checksum mismatch')
    records = [dict(line.split(': ', 1) for line in b.splitlines() if ': ' in line)
               for b in index.read_text().strip().split('\n\n')]
    record = next(r for r in records if r['Package'] == spec['package'])
    package = public/record['Filename']
    if sha(package) != record['SHA256'] or record['Version'] != spec['version']:
        raise RuntimeError('Published package differs from configured baseline')
    root = WORK/(app+'-rehearsal-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    root.mkdir(); (root/'dist').mkdir()
    for name in ('probes', 'ports'):
        shutil.copytree(ROOT/name, root/name, ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(package, root/'dist'/package.name)
    state = dict(app=app, package=spec['package'], version=spec['version'], revision=spec['revision'],
                 baseline=spec, status='built', rehearsal=True, package_file='dist/'+package.name,
                 package_sha256=sha(package))
    write(root/'candidate.json', state); write(root/'build-inputs.json', snapshot(root))
    print('Rehearsal: '+str(root), flush=True)
    verify(root, args)


def release_gate(root, state):
    if state.get('rehearsal'):
        raise RuntimeError('Rehearsals can never be published')
    package = unchanged(root, state)
    for name in ('host', 'target'):
        receipt = root/(name+'-result.json')
        if not receipt.is_file():
            raise RuntimeError('Missing '+name+' acceptance evidence; complete host-check and verify before publication')
        result = read(receipt)
        if result.get('passed') is not True or result.get('package_sha256') != state['package_sha256']:
            raise RuntimeError('Missing/current '+name+' acceptance evidence')
    # Tests/runner changes also invalidate target evidence.
    result = read(root/'target-result.json')
    if result.get('runner_sha256') != sha(ROOT/'probes/update_target_check.py') or result.get('runner_sha256') != sha(root/'probes/update_target_check.py'):
        raise RuntimeError('Target runner changed; repeat VAIO verification')
    return package


def stage_public_recipes(candidate_root, destination):
    """Keep the public maintenance checkout usable after a port patch changes."""
    names = read(ROOT/'maintenance/public-files.json')
    copied = []
    for name in names:
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise RuntimeError('Unsafe public recipe path')
        if name == 'maintenance/upstreams.json':
            continue  # Publication writes the advanced baseline separately.
        source = candidate_root/relative
        if not source.is_file():
            source = ROOT/relative
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(name)
    return copied


def publish(path):
    root, state = candidate(path)
    package = release_gate(root, state)
    settings = config()
    public = ROOT/'.build/apt-public'
    if run(['git', '-C', public, 'status', '--porcelain']):
        raise RuntimeError('Public staging checkout must be clean')
    run(['git', '-C', public, 'fetch', 'origin', 'main'])
    if run(['git', '-C', public, 'rev-parse', 'HEAD']) != run(['git', '-C', public, 'rev-parse', 'origin/main']):
        raise RuntimeError('Public checkout differs from origin/main')
    # Refuse overwrites, downgrades and stale baseline updates.
    index = public/'dists/xenial/main/binary-i386/Packages'
    records = [dict(line.split(': ', 1) for line in block.splitlines() if ': ' in line)
               for block in index.read_text().strip().split('\n\n')]
    previous = next(r for r in records if r['Package'] == state['package'])
    if previous['Version'] != state['baseline']['version']:
        raise RuntimeError('Archive advanced since preparation; refresh the baseline')
    if previous['Version'] == state['version']:
        raise RuntimeError('Publication requires a new Debian version')
    # APT/dpkg comparison was performed on the target against the installed version.
    if not read(root/'target-result.json').get('version_newer') or not read(root/'target-result.json').get('archive_version_newer'):
        raise RuntimeError('Candidate version is not newer than installed version')
    if (public/'pool/main'/package.name).exists():
        raise RuntimeError('This package filename already exists; never overwrite a retained version')
    output = root/'apt-stage'
    if output.exists():
        raise RuntimeError('Publication stage already exists; inspect prior attempt before retrying')
    shutil.copytree(public, output, ignore=shutil.ignore_patterns('.git'))
    recipe_paths = stage_public_recipes(root, output)
    # Signing remains on the Mac; builder never sees the signing key.
    tag = state['app']+'-'+state['version'].replace('~', '-')
    run(['python3', ROOT/'probes/build_public_apt.py', package, '--tag', tag, '--output', output], log=root/'signing.log')
    if (output/'KEY-FINGERPRINT.txt').read_text().strip() != settings['signing_fingerprint']:
        raise RuntimeError('Unexpected signing key')
    run(['gpgv', '--keyring', public/'vaio-artcraft-archive-keyring.gpg', output/'dists/xenial/InRelease'])
    old_pool = public/previous['Filename']
    if sha(output/previous['Filename']) != sha(old_pool):
        raise RuntimeError('Last working package was not retained')
    # A complete corresponding source/recipe archive accompanies every release.
    source_archive = root/(tag+'-source.tar.gz')
    with tarfile.open(source_archive, 'w:gz') as archive:
        for name in read(ROOT/'maintenance/public-files.json'):
            path = root/name
            if not path.exists():
                path = ROOT/name
            archive.add(path, arcname=name)
        archive.add(root/'candidate.json', arcname='candidate.json')
        archive.add(root/'.build'/(state['app']+'-port')/'Cargo.lock', arcname='downstream/Cargo.lock')
        source = root/'upstream'/source_name(state['app'])
        data = subprocess.check_output(['git', '-C', str(source), 'archive', state['revision']])
        with tarfile.open(fileobj=io.BytesIO(data)) as upstream:
            for member in upstream:
                contents = upstream.extractfile(member) if member.isfile() else None
                member.name = 'upstream/'+source_name(state['app'])+'/'+member.name
                archive.addfile(member, contents)
    notes = root/'release-notes.md'
    notes.write_text('Unofficial Xenial i386 '+state['app']+' '+state['version']+' update.\n\n'
                     'Source: https://github.com/'+state['baseline']['repo']+'/tree/'+state['revision']+'\n\n'
                     'Built for Atom/glibc 2.23; isolated real-VAIO editing/export/native-dialog checks passed. '
                     'Host workspace tests exclude xtask and the GPU UI crate. '
                     'Upstream alpha/pre-alpha limitations and external-file risks remain.\n\n'
                     'Package SHA256: '+state['package_sha256']+'\n'
                     'Previous package retained: '+previous['Filename']+'\n')
    run(['gh', 'release', 'create', tag, package, source_archive, '--repo', settings['public_repo'],
         '--draft', '--title', state['app']+' '+state['version'], '--notes-file', notes])
    # Back up prior signed metadata locally before changing the tracked archive.
    shutil.copytree(public/'dists', root/'previous-dists')
    for name in ('dists', 'pool'):
        shutil.copytree(output/name, public/name, dirs_exist_ok=True)
    for name in recipe_paths:
        destination = public/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output/name, destination)
    updated = json.loads(json.dumps(settings))
    updated['apps'][state['app']]['revision'] = state['revision']
    updated['apps'][state['app']]['version'] = state['version']
    write(public/'maintenance/upstreams.json', updated)
    summary = {k: read(root/'target-result.json').get(k) for k in
               ('passed', 'package_sha256', 'steps', 'measurements', 'version_newer', 'archive_version_newer')}
    summary.update(source_revision=state['revision'], version=state['version'])
    write(public/('notes/updates/'+tag+'.json'), summary)
    text = (public/'README.md').read_text()
    text = text.replace('| '+state['package']+' | '+previous['Version']+' |',
                        '| '+state['package']+' | '+state['version']+' |')
    (public/'README.md').write_text(text)
    run(['git', '-C', public, 'add', 'dists', 'pool', 'maintenance/upstreams.json', 'notes/updates/'+tag+'.json', 'README.md']+recipe_paths)
    run(['git', '-C', public, 'commit', '-m', 'Publish verified '+tag])
    run(['git', '-C', public, 'push', 'origin', 'main'])
    run(['gh', 'release', 'edit', tag, '--repo', settings['public_repo'], '--draft=false'])
    # Move only the selected baseline after successful publication. Keep recipes' defaults historical;
    # future maintenance builds use the explicit candidate specification.
    settings['apps'][state['app']]['revision'] = state['revision']
    settings['apps'][state['app']]['version'] = state['version']
    write(CONFIG, settings)
    write(root/'publication.json', {'published': True, 'tag': tag, 'commit': run(['git', '-C', public, 'rev-parse', 'HEAD']),
                                  'previous_package': previous['Filename']})
    print('Published '+tag+'; previous package retained for rollback')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('check'); p.add_argument('apps', nargs='*', choices=list(config()['apps']))
    p = sub.add_parser('prepare'); p.add_argument('app', choices=list(config()['apps'])); p.add_argument('--ref', required=True); p.add_argument('--version', required=True)
    for name in ('build', 'host-check', 'verify', 'publish'):
        p = sub.add_parser(name); p.add_argument('candidate', type=Path)
        if name == 'verify':
            p.add_argument('--ssh', required=True, help='Existing SSH alias or user@host; never a password')
            p.add_argument('--identity', type=Path)
    p = sub.add_parser('run'); p.add_argument('app', choices=list(config()['apps'])); p.add_argument('--ref', required=True); p.add_argument('--version', required=True); p.add_argument('--ssh', required=True); p.add_argument('--identity', type=Path); p.add_argument('--publish', action='store_true')
    p = sub.add_parser('rehearse'); p.add_argument('app', choices=list(config()['apps'])); p.add_argument('--ssh', required=True); p.add_argument('--identity', type=Path)
    args = parser.parse_args()
    with locked():
        if args.command == 'check':
            return check(args.apps or list(config()['apps']))
        if args.command == 'prepare':
            prepare(args.app, args.ref, args.version)
        elif args.command == 'build':
            build(args.candidate)
        elif args.command == 'host-check':
            host_check(args.candidate)
        elif args.command == 'verify':
            verify(args.candidate, args)
        elif args.command == 'publish':
            publish(args.candidate)
        elif args.command == 'rehearse':
            rehearse(args.app, args)
        elif args.command == 'run':
            root = prepare(args.app, args.ref, args.version)
            build(root)
            host_check(root)
            verify(root, args)
            if args.publish:
                publish(root)
            else:
                print('Verified candidate retained locally: '+str(root))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('STOP: '+str(error), file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(str(error.stderr)[-3000:], file=sys.stderr)
        sys.exit(1)
