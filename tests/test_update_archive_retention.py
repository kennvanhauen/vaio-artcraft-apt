import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('retention',Path(__file__).resolve().parents[1]/'probes/retire_apt_packages.py')
retention=importlib.util.module_from_spec(spec);spec.loader.exec_module(retention)

class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'public';self.pool=self.root/'pool/main';self.pool.mkdir(parents=True)
        self.index=self.root/'dists/xenial/main/binary-i386/Packages';self.index.parent.mkdir(parents=True)
        self.index.write_text('Filename: pool/main/current.deb\n')
        (self.pool/'current.deb').write_bytes(b'current');(self.pool/'old.deb').write_bytes(b'old')
        self.backup=Path(self.tmp.name)/'backup';self.backup.mkdir();(self.backup/'old.deb').write_bytes(b'old')
        self.plan=Path(self.tmp.name)/'plan.json'
    def write_plan(self,name):
        self.plan.write_text(json.dumps(dict(index_sha256=retention.sha(self.index),public_head='head',files=[dict(filename='pool/main/'+name,sha256=retention.sha(self.pool/name))])))
    def test_only_unindexed_packages_are_selected(self):
        self.assertEqual(retention.select(self.index,self.pool),[self.pool/'old.deb'])
    def test_missing_current_package_stops_retirement(self):
        self.index.write_text('Filename: pool/main/missing.deb\n')
        with self.assertRaisesRegex(RuntimeError,'missing'):retention.select(self.index,self.pool)
    def test_plan_cannot_remove_an_indexed_package(self):
        self.write_plan('current.deb')
        with patch.object(retention,'PUBLIC',self.root),patch.object(retention,'BACKUP',self.backup),patch.object(retention.subprocess,'check_output',side_effect=['head','']),patch.object(retention.subprocess,'run') as mutate:
            with self.assertRaisesRegex(RuntimeError,'indexed'):retention.apply(self.plan)
            mutate.assert_not_called()
        self.assertTrue((self.pool/'current.deb').exists())
    def test_changed_backup_stops_before_any_removal(self):
        self.write_plan('old.deb');(self.backup/'old.deb').write_bytes(b'changed')
        with patch.object(retention,'PUBLIC',self.root),patch.object(retention,'BACKUP',self.backup),patch.object(retention.subprocess,'check_output',side_effect=['head','']),patch.object(retention.subprocess,'run') as mutate:
            with self.assertRaisesRegex(RuntimeError,'changed'):retention.apply(self.plan)
            mutate.assert_not_called()
        self.assertTrue((self.pool/'old.deb').exists())
    def test_corrupt_previous_map_stops_before_any_removal(self):
        self.write_plan('old.deb');(self.root/'retired-packages.json').write_text('broken json')
        with patch.object(retention,'PUBLIC',self.root),patch.object(retention,'BACKUP',self.backup),patch.object(retention.subprocess,'check_output',side_effect=['head','']),patch.object(retention.subprocess,'run') as mutate:
            with self.assertRaises(json.JSONDecodeError):retention.apply(self.plan)
            mutate.assert_not_called()
        self.assertTrue((self.pool/'old.deb').exists())
