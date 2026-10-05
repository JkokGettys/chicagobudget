"""Recovery of pinned raw files from the versioned publication."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from build import inputs


class PublishedInputsTest(unittest.TestCase):
    def test_restore_and_reject_corrupt_snapshot(self):
        original = inputs.ROOT, inputs.MANIFEST, inputs.PUBLIC_SOURCES
        try:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                inputs.ROOT = root
                inputs.MANIFEST = root / 'build/inputs.sha256'
                inputs.PUBLIC_SOURCES = root / 'data/public/2026/sources'
                inputs.MANIFEST.parent.mkdir(parents=True)
                source = inputs.PUBLIC_SOURCES / 'raw/cps/sample.json'
                source.parent.mkdir(parents=True)
                source.write_bytes(b'public original')
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                inputs.MANIFEST.write_text(f'{digest}  raw/cps/sample.json\n')
                self.assertEqual(inputs.verify(), ['raw/cps/sample.json'])
                inputs.restore_published(inputs.verify())
                self.assertEqual(inputs.verify(), [])
                target = root / 'raw/cps/sample.json'
                target.unlink()
                source.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                    inputs.restore_published(inputs.verify())
                self.assertFalse(target.exists())
        finally:
            inputs.ROOT, inputs.MANIFEST, inputs.PUBLIC_SOURCES = original

    def test_restore_roster_checks_catalog(self):
        original = inputs.ROOT, inputs.PUBLIC_SOURCES, inputs.ROSTERS
        try:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                inputs.ROOT = root
                inputs.PUBLIC_SOURCES = root / 'data/public/2026/sources'
                inputs.ROSTERS = ('data/people/roster.json',)
                source = inputs.PUBLIC_SOURCES / inputs.ROSTERS[0]
                source.parent.mkdir(parents=True)
                source.write_bytes(b'{"name":"Public Source"}')
                entry = {'path': 'sources/' + inputs.ROSTERS[0],
                         'origin': inputs.ROSTERS[0], 'bytes': source.stat().st_size,
                         'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
                catalog = root / 'data/public/2026/catalog.json'
                catalog.write_text(json.dumps({'files': [entry]}))
                inputs.restore_rosters()
                self.assertEqual((root / inputs.ROSTERS[0]).read_bytes(), source.read_bytes())
                (root / inputs.ROSTERS[0]).unlink()
                source.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                    inputs.restore_rosters()
                self.assertFalse((root / inputs.ROSTERS[0]).exists())
        finally:
            inputs.ROOT, inputs.PUBLIC_SOURCES, inputs.ROSTERS = original


if __name__ == '__main__':
    unittest.main()
