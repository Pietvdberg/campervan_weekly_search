import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo, BadZipFile

spec = importlib.util.spec_from_file_location('artifact_extract', Path(__file__).parent / '.github/actions/download-artifact/extract.py')
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)


class ArtifactExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.archives = self.root / 'archives'
        self.archives.mkdir()
        self.destination = self.root / 'restored'

    def archive(self, entries):
        with ZipFile(self.archives / 'download', 'w') as archive:
            for name, content in entries:
                archive.writestr(name, content)

    def test_hidden_state_and_mail_state_roundtrip(self):
        self.archive([('.search-state/history.json', '{"schema_version":1}'), ('mail_delivery_state.json', '{"status":"sent_confirmed"}')])
        root = extractor.extract(self.archives, self.destination)
        self.assertEqual(root, self.destination)
        self.assertEqual((root / '.search-state/history.json').read_text(), '{"schema_version":1}')
        self.assertIn('sent_confirmed', (root / 'mail_delivery_state.json').read_text())

    def test_traversal_is_rejected_before_any_file_is_written(self):
        self.archive([('good.json', '{}'), ('../escaped.json', '{}')])
        with self.assertRaises(ValueError):
            extractor.extract(self.archives, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertFalse((self.root / 'escaped.json').exists())

    def test_symlink_member_and_existing_symlink_cannot_escape(self):
        member = ZipInfo('link')
        member.create_system = 3
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.archive([(member, '../outside')])
        with self.assertRaises(ValueError):
            extractor.extract(self.archives, self.destination)
        self.archive([('link/file.json', '{}')])
        self.destination.mkdir()
        (self.destination / 'link').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            extractor.extract(self.archives, self.destination)
        self.assertFalse((self.root / 'file.json').exists())

    def test_size_limit_and_conflicting_parent_are_rejected(self):
        self.archive([('large.json', 'x' * 20)])
        with patch.object(extractor, 'MAX_BYTES', 10), self.assertRaises(ValueError):
            extractor.extract(self.archives, self.destination)
        self.archive([('parent', 'x'), ('parent/child.json', '{}')])
        with self.assertRaises(ValueError):
            extractor.extract(self.archives, self.destination)
        self.assertFalse(self.destination.exists())

    def test_corrupt_crc_does_not_replace_existing_state(self):
        self.archive([('history.json', 'original-data')])
        archive = self.archives / 'download'
        archive.write_bytes(archive.read_bytes().replace(b'original-data', b'corrupt--data'))
        self.destination.mkdir()
        (self.destination / 'history.json').write_text('previous good state')
        with self.assertRaises(BadZipFile):
            extractor.extract(self.archives, self.destination)
        self.assertEqual((self.destination / 'history.json').read_text(), 'previous good state')
        self.assertEqual(len(list(self.destination.iterdir())), 1)

    def test_ambiguous_download_and_absolute_windows_paths_are_rejected(self):
        self.archive([('C:\\temp\\unsafe.json', '{}')])
        with self.assertRaises(ValueError):
            extractor.extract(self.archives, self.destination)
        (self.archives / 'another').write_text('unexpected')
        with self.assertRaises(ValueError):
            extractor.extract(self.archives, self.destination)
