"""Every maintained application must be reachable and manageable in the VAIO launcher."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LauncherCoverageTests(unittest.TestCase):
    def test_every_maintained_port_has_a_card_open_target_and_apt_permission(self):
        apps = json.loads((ROOT/'maintenance/upstreams.json').read_text())['apps']
        expected = {name: spec['package'] for name, spec in apps.items() if name != 'launcher'}
        backend = (ROOT/'ports/launcher-vaio/src/apt.rs').read_text()
        entries = dict(re.findall(r'ManagedApp\s*\{\s*id:\s*"([^"]+)".*?package:\s*"([^"]+)"', backend))
        self.assertEqual(entries, expected, 'An application port is missing its launcher backend entry')
        main = (ROOT/'ports/launcher-vaio/src/main.rs').read_text()
        retained = re.search(r'launcher\.retain_apps\(&\[([^]]+)\]\)', main).group(1)
        self.assertEqual(set(re.findall(r'"([^"]+)"', retained)), set(expected), 'A maintained port is hidden from the launcher')
        helper = (ROOT/'ports/launcher-vaio/apt-action').read_text()
        permitted = re.search(r'case "\$package" in ([^)]+)\)', helper).group(1).split('|')
        self.assertEqual(set(permitted), set(expected.values()), 'Launcher APT permissions omit a maintained port')
        limit = int(re.search(r'"\$#" -gt (\d+)', helper).group(1))
        self.assertGreaterEqual(limit, len(expected), 'The APT batch limit excludes part of the suite')


if __name__ == '__main__':
    unittest.main()
