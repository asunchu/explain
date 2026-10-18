import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('sync', Path(__file__).resolve().parents[1] / 'scripts/sync-defaults.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)
class SyncTests(unittest.TestCase):
    def test_preserves_surrounding_content_and_is_idempotent(self):
        old = 'before\n' + sync.START + '\nold\n' + sync.END + '\nafter\n'
        new = sync.merge(old, 'new')
        self.assertTrue(new.startswith('before\n'))
        self.assertTrue(new.endswith('\nafter\n'))
        self.assertEqual(sync.merge(new, 'new'), new)
    def test_rejects_invalid_markers(self):
        for text in (sync.START, sync.END + sync.START, (sync.START + sync.END) * 2):
            with self.assertRaises(ValueError): sync.merge(text, 'new')
