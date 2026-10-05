"""Regression tests for reporting integrity; none execute Explain or an AI model."""
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('evaluate', ROOT / 'scripts/evaluate.py')
evaluate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate)


class ReporterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / 'run'
        subprocess.run([sys.executable, str(ROOT / 'scripts/evaluate.py'), 'prepare',
                        '--harness', 'codex', '--model', 'synthetic-test-only',
                        '--harness-version', 'test', '--case', 'brief-definition',
                        '--out', str(self.run)], check=True, capture_output=True)
        self.path = self.run / 'results.json'
        self.data = json.loads(self.path.read_text())

    def report(self):
        self.path.write_text(json.dumps(self.data))
        with contextlib.redirect_stdout(io.StringIO()):
            return evaluate.summarize(self.path)

    def rated(self):
        self.data['reviewer'] = 'synthetic fixture'
        row = self.data['cases'][0]
        row['observed_format'] = 'prose'
        row['transcript'] = 'brief-definition/transcript.txt'
        (self.run / row['transcript']).write_text('Synthetic reporter fixture, not a model output.')
        for item in row['criteria'].values():
            item.update(status='pass', evidence='Synthetic fixture evidence; not a behavioral result.')
        return row

    def test_suite_loads(self):
        self.assertEqual(len(evaluate.load_suite()['cases']), 23)

    def test_unrun_is_incomplete(self):
        self.assertEqual(self.report(), 2)

    def test_complete_record_passes(self):
        self.rated()
        self.assertEqual(self.report(), 0)

    def test_failure_dominates_blocked(self):
        row = self.rated()
        row['criteria']['format']['status'] = 'fail'
        row['criteria']['length']['status'] = 'blocked'
        self.assertEqual(self.report(), 1)

    def test_blocked_is_not_pass(self):
        row = self.rated()
        row['criteria']['format']['status'] = 'blocked'
        self.assertEqual(self.report(), 2)

    def test_rejects_pass_without_evidence(self):
        row = self.rated()
        row['criteria']['format']['evidence'] = ''
        with self.assertRaisesRegex(ValueError, 'Evidence required'):
            self.report()

    def test_rejects_missing_transcript(self):
        row = self.rated()
        (self.run / row['transcript']).unlink()
        with self.assertRaisesRegex(ValueError, 'transcript'):
            self.report()

    def test_rejects_wrong_format(self):
        row = self.rated()
        row['observed_format'] = 'video'
        with self.assertRaisesRegex(ValueError, 'Unexpected format'):
            self.report()

    def test_rejects_omitted_criterion(self):
        row = self.rated()
        del row['criteria']['length']
        with self.assertRaisesRegex(ValueError, 'Missing/extra criteria'):
            self.report()

    def test_rejects_duplicate_case(self):
        self.data['cases'].append(self.data['cases'][0])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.report()

    def test_rejects_omitted_selected_case(self):
        (self.run / 'selection.json').write_text(json.dumps(['brief-definition', 'relationships']))
        with self.assertRaisesRegex(ValueError, 'Selected cases'):
            self.report()

    def test_rejects_changed_candidate(self):
        (self.run / 'candidate-skill/SKILL.md').write_text('modified')
        with self.assertRaisesRegex(ValueError, 'Candidate skill changed'):
            self.report()

    def test_rejects_overwrite(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/evaluate.py'), 'prepare',
                                 '--harness', 'codex', '--model', 'test', '--harness-version', 'test',
                                 '--out', str(self.run)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 3)
        self.assertIn('already exists', result.stderr)


if __name__ == '__main__':
    unittest.main()
