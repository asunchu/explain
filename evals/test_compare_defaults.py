"""Test trial isolation and evidence capture without calling a model."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('compare_defaults', Path(__file__).resolve().parents[1] / 'scripts/compare_defaults.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class TrialTests(unittest.TestCase):
    def test_external_skill_access_covers_symlink_and_target_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            target = home / '.codex/skills/explain'
            target.mkdir(parents=True)
            link = home / '.config/opencode/skills/explain'
            link.parent.mkdir(parents=True)
            link.symlink_to(target, target_is_directory=True)
            with patch.object(runner.Path, 'home', return_value=home):
                rules = runner.opencode_config()['agents']['build']['permissions']
            external = {r['resource'] for r in rules if r['action'] == 'external_directory'}
            self.assertEqual(external, {str(link) + '/*', str(target) + '/*'})
            self.assertFalse(any(r['action'] in ('edit', 'shell') and r['effect'] == 'allow' for r in rules))

    def test_keeps_working_directory_and_records_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = root / 'fake-cli'
            fake.write_text('''#!/usr/bin/env python3
import json, os
from pathlib import Path
assert os.getcwd() == os.environ['PWD']
assert Path('CLAUDE.md').read_text() == 'test instructions'
Path('unexpected.txt').write_text('record this side effect')
print(json.dumps({'type': 'result', 'result': 'test answer'}))
''')
            fake.chmod(0o755)
            trial = root / 'trial'
            case = {'prompt': 'test prompt', 'fixtures': {'input.txt': 'fixture'}, 'criteria': {'scope': 'no edits'}}
            result = runner.run_trial('claude-code', 'test-model', case, trial, 'test instructions', 10, str(fake))
            self.assertEqual(result['exit_code'], 0)
            self.assertEqual((trial / 'answer.md').read_text(), 'test answer')
            self.assertNotIn('unexpected.txt', result['input_sha256'])
            self.assertIn('unexpected.txt', result['output_sha256'])
            self.assertEqual(result['review']['scope']['status'], 'pending')
            self.assertEqual(json.loads((trial / 'command.json').read_text())[0], str(fake))

    def test_refuses_fixture_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = {'prompt': 'test', 'fixtures': {'../escape.txt': 'bad'}, 'criteria': {}}
            with self.assertRaisesRegex(ValueError, 'escapes'):
                runner.run_trial('codex', 'unused', case, Path(tmp) / 'trial', 'instructions', 1)
            self.assertFalse((Path(tmp) / 'trial/escape.txt').exists())


if __name__ == '__main__':
    unittest.main()
