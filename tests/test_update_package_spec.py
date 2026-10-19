import importlib.util
from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('package_spec', Path(__file__).resolve().parents[1]/'probes/update_package_spec.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class PackageMetadataTests(unittest.TestCase):
    def test_historical_defaults_unchanged(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(m.candidate_spec(Path('/unused'), 'cadcraft', '0.9.0~vaio1', 'old'), ('0.9.0~vaio1', 'old'))

    def test_override_is_bound_to_selected_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root/'spec.json'
            data = {'app': 'cadcraft', 'version': '0.9.1~vaio1', 'revision': 'a'*40}
            path.write_text(json.dumps(data))
            with patch.dict(os.environ, {'VAIO_PACKAGE_SPEC': str(path)}), patch.object(m.subprocess, 'check_output', return_value='a'*40+'\n'):
                self.assertEqual(m.candidate_spec(root, 'cadcraft', 'old', 'old'), ('0.9.1~vaio1', 'a'*40))
                with self.assertRaises(SystemExit): m.candidate_spec(root, 'wordcraft', 'old', 'old')
            with patch.dict(os.environ, {'VAIO_PACKAGE_SPEC': str(path)}), patch.object(m.subprocess, 'check_output', return_value='b'*40):
                with self.assertRaises(SystemExit): m.candidate_spec(root, 'cadcraft', 'old', 'old')
            data['version'] = '0.9.1;unsafe'
            path.write_text(json.dumps(data))
            with patch.dict(os.environ, {'VAIO_PACKAGE_SPEC': str(path)}):
                with self.assertRaises(SystemExit): m.candidate_spec(root, 'cadcraft', 'old', 'old')

if __name__ == '__main__': unittest.main()
