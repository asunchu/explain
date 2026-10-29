"""Test trial isolation and evidence capture without calling a model."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from loading import routing

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

    def test_local_skill_and_process_plugin_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = root / 'fake-cli'
            fake.write_text("#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\nassert Path('.claude/skills/explain/CORE.md').is_file()\nassert not Path('CLAUDE.md').exists()\nsettings=json.loads(sys.argv[sys.argv.index('--settings')+1])\nassert settings['enabledPlugins']['explanatory-output-style@claude-plugins-official'] is False\nprint(json.dumps({'type':'result','result':'ok'}))\n")
            fake.chmod(0o755)
            result = runner.run_trial('claude-code', 'test', {'prompt':'test','fixtures':{},'criteria':{}},
                                      root / 'trial', '', 10, str(fake), True, True)
            self.assertEqual(result['exit_code'], 0)
            self.assertEqual(result['input_sha256'], result['output_sha256'])

    def test_routed_trial_uses_local_path_and_excludes_runtime_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source = root / 'repo/skills/explain'
            source.mkdir(parents=True)
            (source / 'SKILL.md').write_text('local skill')
            (source / 'node_modules').mkdir()
            (source / 'node_modules/unrelated.txt').write_text('exclude')
            fake = root / 'fake-cli'
            fake.write_text("#!/usr/bin/env python3\nimport json\nfrom pathlib import Path\nskill=Path.cwd()/'.claude/skills/explain'\nassert str(skill/'SKILL.md') in Path('CLAUDE.md').read_text()\nassert (skill/'SKILL.md').read_text()=='local skill'\nassert not (skill/'node_modules').exists()\nprint(json.dumps({'type':'result','result':'ok'}))\n")
            fake.chmod(0o755)
            with patch.object(runner, 'ROOT', root / 'repo'):
                result = runner.run_trial('claude-code', 'test', {'prompt':'test','fixtures':{},'criteria':{}},
                                          root / 'trial', '', 10, str(fake), True, False, True)
            self.assertEqual(result['exit_code'], 0)
            self.assertEqual(result['input_sha256'], result['output_sha256'])

    def test_empty_success_is_not_a_completed_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = root / 'fake-cli'
            fake.write_text("#!/usr/bin/env python3\nprint('{}')\n")
            fake.chmod(0o755)
            result = runner.run_trial('opencode', 'test',
                {'prompt': 'test', 'fixtures': {}, 'criteria': {}},
                root / 'trial', '', 10, str(fake))
            self.assertEqual(result['status'], 'response_missing')
            self.assertFalse(result['has_answer'])
            self.assertEqual(result['exit_code'], 0)

    def test_empty_response_continues_without_retry_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = root / 'fake-cli'
            fake.write_text("#!/usr/bin/env python3\nimport json,sys\nif '--version' in sys.argv: print('test version')\nelif sys.argv[-1]=='second': print(json.dumps({'type':'text','part':{'text':'answer'}}))\n")
            fake.chmod(0o755)
            core = root / 'core.md'
            core.write_text('test instructions')
            suite = root / 'suite.json'
            suite.write_text(json.dumps({'cases': [
                {'id': name, 'prompt': name, 'fixtures': {}, 'criteria': {}}
                for name in ['first', 'second']]}))
            out = root / 'results'
            argv = ['compare_defaults.py', '--harness', 'opencode', '--model', 'test',
                    '--executable', str(fake), '--baseline-default', str(core),
                    '--candidate-default', str(core), '--candidate-only',
                    '--suite', str(suite), '--repeats', '1', '--out', str(out)]
            with patch.object(sys, 'argv', argv):
                code = runner.main()
            self.assertEqual(code, 2)
            executions = sorted(out.glob('candidate/repeat-1/*/execution.json'))
            self.assertEqual(len(executions), 2)
            statuses = [json.loads(f.read_text())['status'] for f in executions]
            self.assertEqual(statuses, ['response_missing', 'completed'])

    def test_reported_error_is_not_an_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = root / 'fake-cli'
            fake.write_text("#!/usr/bin/env python3\nimport json\nprint(json.dumps({'type':'result','is_error':True,'result':'quota error'}))\n")
            fake.chmod(0o755)
            result = runner.run_trial('claude-code', 'test',
                {'prompt': 'test', 'fixtures': {}, 'criteria': {}},
                root / 'trial', '', 10, str(fake))
            self.assertEqual(result['status'], 'infrastructure_error')

    def test_refuses_fixture_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = {'prompt': 'test', 'fixtures': {'../escape.txt': 'bad'}, 'criteria': {}}
            with self.assertRaisesRegex(ValueError, 'escapes'):
                runner.run_trial('codex', 'unused', case, Path(tmp) / 'trial', 'instructions', 1)
            self.assertFalse((Path(tmp) / 'trial/escape.txt').exists())


if __name__ == '__main__':
    unittest.main()
