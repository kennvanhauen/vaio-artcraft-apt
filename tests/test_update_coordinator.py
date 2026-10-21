"""Release gates and isolation checks; no network, signing, APT or user documents."""
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('coordinator', ROOT/'probes/maintain_updates.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
spec = importlib.util.spec_from_file_location('target', ROOT/'probes/update_target_check.py')
target = importlib.util.module_from_spec(spec); spec.loader.exec_module(target)


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in ('ports', 'probes', 'dist'):
            (self.root/name).mkdir()
        (self.root/'ports/cadcraft-xenial.patch').write_text('patch')
        (self.root/'probes/update_target_check.py').write_bytes((ROOT/'probes/update_target_check.py').read_bytes())
        package = self.root/'dist/candidate.deb'; package.write_bytes(b'candidate')
        self.state = {'package_file': 'dist/candidate.deb', 'package_sha256': m.sha(package)}
        m.write(self.root/'candidate.json', self.state)
        m.write(self.root/'build-inputs.json', m.snapshot(self.root))
        for name in ('host', 'target'):
            m.write(self.root/(name+'-result.json'), {'passed': True,
                'package_sha256': self.state['package_sha256'],
                'runner_sha256': m.sha(ROOT/'probes/update_target_check.py')})

    def tearDown(self):
        self.tmp.cleanup()

    def test_rehearsal_is_never_publishable(self):
        self.state['rehearsal'] = True
        with self.assertRaises(RuntimeError): m.release_gate(self.root, self.state)

    def test_matching_evidence_passes(self):
        self.assertEqual(m.release_gate(self.root, self.state), self.root/'dist/candidate.deb')

    def test_missing_host_evidence_stops_release(self):
        (self.root/'host-result.json').unlink()
        with self.assertRaisesRegex(RuntimeError, 'Missing host acceptance'):
            m.release_gate(self.root, self.state)

    def test_failed_target_stops_release(self):
        m.write(self.root/'target-result.json', {'passed': False})
        with self.assertRaises(RuntimeError): m.release_gate(self.root, self.state)

    def test_changed_package_invalidates_results(self):
        (self.root/'dist/candidate.deb').write_bytes(b'new binary')
        with self.assertRaises(RuntimeError): m.release_gate(self.root, self.state)

    def test_changed_patch_invalidates_results(self):
        (self.root/'ports/cadcraft-xenial.patch').write_text('revised patch')
        with self.assertRaises(RuntimeError): m.release_gate(self.root, self.state)

    def test_stale_result_stops_release(self):
        m.write(self.root/'host-result.json', {'passed': True, 'package_sha256': 'old'})
        with self.assertRaises(RuntimeError): m.release_gate(self.root, self.state)

    def test_runner_change_requires_retest(self):
        data = m.read(self.root/'target-result.json'); data['runner_sha256'] = 'old'
        m.write(self.root/'target-result.json', data)
        with self.assertRaises(RuntimeError): m.release_gate(self.root, self.state)

    def test_failed_reverification_invalidates_previous_pass(self):
        import subprocess
        class Args:
            identity = None
            ssh = 'vaio-test-alias'
        with patch.object(m, 'WORK', self.root), patch.object(m, 'remote_directory', return_value='/tmp/vaio-update-fixture'), patch.object(m, 'run', side_effect=subprocess.CalledProcessError(255, ['ssh'])):
            with self.assertRaises(subprocess.CalledProcessError): m.verify(self.root, Args())
        self.assertFalse(m.read(self.root/'target-result.json')['passed'])
        self.assertEqual(len(list((self.root/'target-history').glob('*.json'))), 1)

    def test_rebuild_archives_acceptance_before_new_build(self):
        m.invalidate_acceptance(self.root)
        self.assertFalse((self.root/'host-result.json').exists())
        self.assertFalse((self.root/'target-result.json').exists())
        self.assertEqual(len(list((self.root/'acceptance-history').glob('*/host-result.json'))), 1)
        with self.assertRaises(RuntimeError): m.release_gate(self.root, self.state)

    def test_published_candidate_cannot_be_rebuilt(self):
        (self.root/'publication.json').write_text('{}')
        with patch.object(m, 'candidate', return_value=(self.root, dict(status='built'))):
            with self.assertRaisesRegex(RuntimeError, 'Published candidates'): m.build(self.root)

    def test_host_git_inventory_uses_upstream_and_includes_added_assets(self):
        import os
        import subprocess
        source = self.root/'upstream/cadcraft'
        source.mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', str(source)], check=True)
        (source/'tracked.svg').write_text('synthetic asset')
        subprocess.run(['git', '-C', str(source), 'add', 'tracked.svg'], check=True)
        subprocess.run(['git', '-C', str(source), '-c', 'user.name=Test', '-c',
                        'user.email=test@example.invalid', 'commit', '-qm', 'fixture'], check=True)
        tree = self.root/'port'; tree.mkdir()
        (tree/'tracked.svg').write_text('synthetic asset')
        (tree/'new.svg').write_text('new synthetic asset')
        env = m.host_git_environment(self.root, dict(app='cadcraft', revision='HEAD'), tree, os.environ)
        files = subprocess.check_output(['git', 'ls-files', '--cached', '--others',
                                         '--exclude-standard'], cwd=tree, env=env, text=True)
        self.assertEqual(set(files.splitlines()), {'tracked.svg', 'new.svg'})

    def test_compiled_source_changes_invalidate_evidence(self):
        source = self.root/'.build/cadcraft-port/src/lib.rs'; source.parent.mkdir(parents=True)
        source.write_text('original source')
        m.write(self.root/'build-inputs.json', m.snapshot(self.root))
        source.write_text('changed source')
        with self.assertRaises(RuntimeError): m.release_gate(self.root, self.state)

    def test_unrelated_path_is_rejected(self):
        with patch.object(m, 'WORK', self.root/'updates'):
            with self.assertRaises(RuntimeError): m.candidate(self.root)

    def test_concurrent_coordinator_is_rejected(self):
        with patch.object(m, 'WORK', self.root/'updates'):
            with m.locked():
                with self.assertRaises(RuntimeError):
                    with m.locked(): pass

    def test_patch_isolated_from_enclosing_git_checkout(self):
        import subprocess
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root/'file.txt').write_text('do not change parent\n')
        tree = self.root/'nested/tree'; tree.mkdir(parents=True)
        (tree/'file.txt').write_text('old\n')
        diff = self.root/'test.patch'
        diff.write_text('--- a/file.txt\n+++ b/file.txt\n@@ -1 +1 @@\n-old\n+new\n')
        m.apply_port_patch(tree, diff)
        self.assertEqual((tree/'file.txt').read_text(), 'new\n')
        self.assertEqual((self.root/'file.txt').read_text(), 'do not change parent\n')

    def test_lock_overlay_preserves_new_upstream_dependencies(self):
        import subprocess
        base = 'version = 4\n\n[[package]]\nname = "old"\nversion = "1.0.0"\n'
        port = base+'\n[[package]]\nname = "vaio"\nversion = "1.0.0"\n'
        new = 'version = 4\n\n[[package]]\nname = "new-upstream"\nversion = "2.0.0"\n\n'+base.split('\n\n', 1)[1]
        tree = self.root/'tree'; tree.mkdir(); (tree/'Cargo.lock').write_text(new)
        patchfile = self.root/'overlay.patch'
        patchfile.write_text(m.lock_overlay(base, port, ''))
        subprocess.run(['git', 'apply', str(patchfile)], cwd=tree, check=True)
        result = (tree/'Cargo.lock').read_text()
        self.assertIn('new-upstream', result); self.assertIn('vaio', result)
        self.assertEqual(m.lock_overlay(base, port, '+++ b/Cargo.lock\n'), '')

    def test_remote_paths_are_typable_without_shift(self):
        self.assertEqual(m.remote_directory(Path('cadcraft-20261019T123456Z')),
                         '/tmp/vaio-update-cadcraft-20261019t123456z')
        with self.assertRaises(RuntimeError): m.remote_directory(Path('candidate;command'))

    def test_no_shell_in_ssh_host(self):
        class Args:
            ssh = 'user@host;touch /tmp/unwanted'
            identity = None
        with self.assertRaises(RuntimeError): m.ssh_args(Args())

    def test_public_recipes_include_acceptance_dependencies(self):
        import json
        files = set(json.loads((ROOT/'maintenance/public-files.json').read_text()))
        required = {'wordcraft_smoke.py', 'native_dialog_test.py', 'vaio_test_support.py',
                    'gridcraft_smoke.py', 'gridcraft_native_dialogs.py',
                    'pdfcraft_smoke.py', 'pdfcraft_native_dialogs.py',
                    'deckcraft_smoke.py', 'deckcraft_native_dialogs.py', 'launcher_eight_open.py'}
        required.update(app+'_'+probe+'.py' for app in ('vectorcraft','designcraft','figcraft','cadcraft')
                        for probe in ('headless','gui','native_dialogs'))
        self.assertTrue({'probes/'+name for name in required} <= files)
        for name in files:
            self.assertNotIn('..', Path(name).parts)
            self.assertTrue((ROOT/name).is_file(), name)

    def test_publication_keeps_rebased_recipe_and_excludes_private_files(self):
        settings = self.root/'maintenance'
        settings.mkdir()
        m.write(settings/'public-files.json', ['ports/cadcraft-xenial.patch',
                'probes/maintain_updates.py', 'maintenance/upstreams.json'])
        (self.root/'probes/maintain_updates.py').write_text('fallback coordinator')
        candidate_root = self.root/'candidate'
        (candidate_root/'ports').mkdir(parents=True)
        (candidate_root/'ports/cadcraft-xenial.patch').write_text('rebased patch')
        (candidate_root/'auth.json').write_text('private fixture: never publish')
        destination = self.root/'public'
        with patch.object(m, 'ROOT', self.root):
            paths = m.stage_public_recipes(candidate_root, destination)
        self.assertEqual((destination/'ports/cadcraft-xenial.patch').read_text(), 'rebased patch')
        self.assertEqual((destination/'probes/maintain_updates.py').read_text(), 'fallback coordinator')
        self.assertNotIn('maintenance/upstreams.json', paths)
        self.assertFalse((destination/'auth.json').exists())

    def test_target_runner_has_python35_syntax(self):
        ast.parse((ROOT/'probes/update_target_check.py').read_text(), feature_version=(3, 5))

    def test_fixture_has_three_pages_and_valid_offsets(self):
        path = self.root/'fixture.pdf'; target.fixture_pdf(path)
        data = path.read_bytes()
        self.assertIn(b'/Count 3', data)
        for number in (1, 2, 3): self.assertIn(('test page %d' % number).encode(), data)
        xref = int(data.split(b'startxref\n')[1].splitlines()[0])
        self.assertTrue(data[xref:].startswith(b'xref\n'))


if __name__ == '__main__':
    unittest.main()
