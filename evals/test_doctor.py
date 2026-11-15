import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/doctor.py'
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location('doctor', SCRIPT)
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.reference = self.base / 'reference'
        self.home = self.base / 'home'
        self.project = self.base / 'project'
        self.reference.mkdir()
        self.home.mkdir()
        self.project.mkdir()
        (self.project / '.git').mkdir()
        self.core = '# Explain core\n\nPreserve meaning.\n'
        self.write(self.reference / 'SKILL.md', '---\nname: explain\n---\nExplain the topic.\n')
        self.write(self.reference / 'CORE.md', self.core)
        self.write(self.reference / 'references/guide.md', 'Read the source.\n')

    @staticmethod
    def write(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def install(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.reference, path)
        return path

    def report(self, harnesses=('codex',), env=None, extra_paths=()):
        return doctor.build_report(self.reference, self.project, home=self.home,
                                   env={} if env is None else env,
                                   harnesses=harnesses, extra_paths=extra_paths)

    def defaults(self, content):
        self.write(self.home / '.codex/AGENTS.md', content)

    def block(self, content):
        return doctor.START + '\n' + content.strip() + '\n' + doctor.END + '\n'

    def global_defaults(self, report):
        return next(item for item in report['harnesses']['codex']['defaults']
                    if item['path'] == str(self.home / '.codex/AGENTS.md'))

    @staticmethod
    def codes(report):
        return {item['code'] for item in report['findings']}

    def test_symlink_aliases_share_one_target(self):
        shared = self.install(self.home / '.agents/skills/explain')
        alias = self.home / '.codex/skills/explain'
        alias.parent.mkdir(parents=True)
        alias.symlink_to(shared, target_is_directory=True)

        report = self.report()

        self.assertEqual(set(report['harnesses']['codex']['candidates']), {str(shared), str(alias)})
        self.assertEqual(report['harnesses']['codex']['distinct_targets'], 1)
        self.assertEqual(report['installations'][str(alias)]['resolved'], str(shared.resolve()))
        self.assertTrue(report['ok'])

    def test_identical_independent_copies_remain_distinct(self):
        shared = self.install(self.home / '.agents/skills/explain')
        legacy = self.install(self.home / '.codex/skills/explain')

        report = self.report()

        self.assertEqual(report['harnesses']['codex']['distinct_targets'], 2)
        self.assertEqual(report['installations'][str(shared)]['fingerprint'],
                         report['installations'][str(legacy)]['fingerprint'])
        self.assertIn('multiple_copies', self.codes(report))
        self.assertFalse(report['ok'])

    def test_reports_content_differences_without_dependency_noise(self):
        installed = self.install(self.home / '.agents/skills/explain')
        (installed / 'references/guide.md').unlink()
        self.write(installed / 'CORE.md', 'A local writing rule.\n')
        self.write(installed / 'local-note.txt', 'A local addition.\n')
        for folder in ('.git', 'node_modules', '.venv', 'models', '__pycache__'):
            self.write(installed / folder / 'ignored.txt', 'Not part of the skill.\n')
        self.write(installed / '.DS_Store', 'Finder metadata.\n')
        self.write(installed / 'cache.pyc', 'Python cache.\n')

        result = self.report()['installations'][str(installed)]

        self.assertEqual(result['state'], 'different')
        self.assertEqual(result['missing'], ['references/guide.md'])
        self.assertEqual(result['changed'], ['CORE.md'])
        self.assertEqual(result['extra'], ['local-note.txt'])
        self.assertEqual(result['errors'], [])

    def test_malformed_package_manifest_shapes_do_not_abort_reporting(self):
        installed = self.install(self.home / '.agents/skills/explain')
        manifest = installed / 'scripts/diagrams/package.json'
        cases = (
            ('invalid JSON', '{broken', None),
            ('null manifest', 'null', None),
            ('array manifest', '[]', None),
            ('string manifest', '"manifest"', None),
            ('number manifest', '42', None),
            ('null dependencies', '{"dependencies": null}', None),
            ('array dependencies', '{"dependencies": []}', None),
            ('string dependencies', '{"dependencies": "pele"}', None),
            ('null version', '{"dependencies": {"pele": null}}', None),
            ('numeric version', '{"dependencies": {"pele": 3}}', None),
            ('object version', '{"dependencies": {"pele": {"version": "1.2.3"}}}', None),
            ('string version', '{"dependencies": {"pele": "1.2.3"}}', '1.2.3'),
        )
        for name, content, expected_version in cases:
            with self.subTest(name=name):
                self.write(manifest, content)

                report = self.report()
                result = report['installations'][str(installed)]

                self.assertEqual(result['pele'], expected_version)
                self.assertEqual(result['state'], 'different')
                self.assertEqual(result['extra'], ['scripts/diagrams/package.json'])
                self.assertIn('installation_different', self.codes(report))

    def test_invalid_candidates_do_not_abort_the_report(self):
        missing = self.base / 'absent'
        broken = self.base / 'broken'
        broken.symlink_to(missing, target_is_directory=True)
        loop = self.base / 'loop'
        loop.symlink_to(loop, target_is_directory=True)
        plain_file = self.base / 'plain-file'
        plain_file.write_text('This is not a skill directory.\n')

        report = self.report(extra_paths=(missing, broken, loop, plain_file))

        states = {path: item['state'] for path, item in report['installations'].items()}
        self.assertEqual(states[str(missing)], 'missing')
        self.assertEqual(states[str(broken)], 'broken_link')
        self.assertEqual(states[str(loop)], 'unreadable')
        self.assertEqual(states[str(plain_file)], 'not_directory')
        for state in ('missing', 'broken_link', 'unreadable', 'not_directory'):
            self.assertIn('installation_' + state, self.codes(report))

    def test_invalid_file_does_not_count_as_another_installation(self):
        self.install(self.home / '.agents/skills/explain')
        plain_file = self.base / 'plain-file'
        plain_file.write_text('This is not a skill directory.\n')

        report = self.report(extra_paths=(plain_file,))

        self.assertEqual(report['harnesses']['codex']['distinct_targets'], 1)
        self.assertNotIn('multiple_copies', self.codes(report))
        self.assertIn('installation_not_directory', self.codes(report))

    def test_marks_default_block_state_without_exposing_other_text(self):
        self.install(self.home / '.agents/skills/explain')
        cases = {
            'current': (self.block(self.core), 'match'),
            'changed': (self.block('Use a different writing rule.'), 'different'),
            'unmanaged': ('A user writing preference.\n', 'unmanaged'),
            'missing_end': (doctor.START + '\n' + self.core, 'invalid_markers'),
            'missing_start': (self.core + doctor.END, 'invalid_markers'),
            'reversed': (doctor.END + '\n' + doctor.START, 'invalid_markers'),
            'repeated': (self.block(self.core) * 2, 'invalid_markers'),
        }
        private_text = 'UNRELATED_PRIVATE_INSTRUCTION'
        for name, (content, expected) in cases.items():
            with self.subTest(name=name):
                self.defaults(private_text + '\n' + content)
                report = self.report()
                self.assertEqual(self.global_defaults(report)['state'], expected)
                self.assertNotIn(private_text, json.dumps(report))
                if expected in ('different', 'invalid_markers'):
                    self.assertIn('defaults_' + expected, self.codes(report))

    def test_broken_default_symlink_is_reported(self):
        self.install(self.home / '.agents/skills/explain')
        path = self.home / '.codex/AGENTS.md'
        path.parent.mkdir(parents=True)
        path.symlink_to(self.base / 'missing-instructions.md')

        report = self.report()

        self.assertEqual(self.global_defaults(report)['state'], 'broken_link')
        self.assertIn('defaults_broken_link', self.codes(report))
        self.assertFalse(report['ok'])

    def test_router_discovers_an_installation_outside_standard_paths(self):
        installed = self.install(self.base / 'custom-installation')
        self.defaults(self.block(self.core.strip() + '\n\n' + doctor.routing(installed)))

        report = self.report()
        default = self.global_defaults(report)

        self.assertEqual(default['state'], 'match')
        self.assertEqual(default['routing'], 'present')
        self.assertEqual(default['route_content'], 'match')
        self.assertEqual(default['routes'][0]['state'], 'exists')
        self.assertEqual(report['harnesses']['codex']['candidates'], [str(installed)])
        self.assertEqual(report['installations'][str(installed)]['state'], 'match')
        self.assertTrue(report['ok'])

    def test_changed_router_text_remains_visible_when_its_target_exists(self):
        installed = self.install(self.base / 'custom-installation')
        router = doctor.routing(installed) + '\nAnnounce every writing check.\n'
        self.defaults(self.block(self.core.strip() + '\n\n' + router))

        report = self.report()
        default = self.global_defaults(report)

        self.assertEqual(default['state'], 'match')
        self.assertEqual(default['routes'][0]['state'], 'exists')
        self.assertEqual(default['route_content'], 'different')
        self.assertFalse(report['ok'])

    def test_reports_broken_relative_and_unrecognized_routes(self):
        self.install(self.home / '.agents/skills/explain')
        cases = (
            ('Read `' + str(self.base / 'absent/SKILL.md') + '`.', 'route_missing'),
            ('Read `relative/explain/SKILL.md`.', 'route_relative_unresolved'),
            ('Read the Explain skill.', 'route_content_different'),
        )
        for router, expected in cases:
            with self.subTest(expected=expected):
                self.defaults(self.block(self.core.strip() + '\n\n## Explanation artifacts\n' + router))
                self.assertIn(expected, self.codes(self.report()))

    def test_finds_explain_frontmatter_in_a_custom_folder(self):
        installed = self.install(self.home / '.agents/skills/writing-guide')
        self.write(self.home / '.agents/skills/unrelated/SKILL.md',
                   '---\nname: unrelated\n---\nAnother skill.\n')

        report = self.report()

        self.assertEqual(report['harnesses']['codex']['candidates'], [str(installed)])
        self.assertTrue(report['ok'])

    def test_honors_explicit_configuration_directories(self):
        env = {
            'CODEX_HOME': str(self.base / 'custom-codex'),
            'CLAUDE_CONFIG_DIR': str(self.base / 'custom-claude'),
            'XDG_CONFIG_HOME': str(self.base / 'custom-config'),
            'OPENCODE_CONFIG_DIR': str(self.base / 'custom-opencode'),
        }
        codex = Path(env['CODEX_HOME'])
        claude = Path(env['CLAUDE_CONFIG_DIR'])
        opencode = Path(env['XDG_CONFIG_HOME']) / 'opencode'
        custom_opencode = Path(env['OPENCODE_CONFIG_DIR'])
        for directory in (codex, claude, opencode, custom_opencode):
            self.install(directory / 'skills/explain')
        for path in (codex / 'AGENTS.md', claude / 'CLAUDE.md',
                     opencode / 'AGENTS.md', custom_opencode / 'AGENTS.md'):
            self.write(path, self.block(self.core))

        report = self.report(harnesses=doctor.HARNESSES, env=env)

        self.assertEqual(report['harnesses']['codex']['candidates'], [str(codex / 'skills/explain')])
        self.assertEqual(report['harnesses']['claude-code']['candidates'], [str(claude / 'skills/explain')])
        self.assertEqual(set(report['harnesses']['opencode']['candidates']),
                         {str(path / 'skills/explain') for path in (opencode, claude, custom_opencode)})
        for harness, expected in (('codex', codex / 'AGENTS.md'),
                                  ('claude-code', claude / 'CLAUDE.md'),
                                  ('opencode', custom_opencode / 'AGENTS.md')):
            defaults = {item['path']: item for item in report['harnesses'][harness]['defaults']}
            self.assertEqual(defaults[str(expected)]['state'], 'match')
        self.assertNotIn(str(self.home / '.claude/skills/explain'), report['installations'])

    def test_project_ancestor_scan_stops_at_the_nearest_worktree(self):
        outside = self.install(self.base / '.agents/skills/explain')
        installed = self.install(self.project / '.agents/skills/explain')
        child = self.project / 'nested/deeper'
        child.mkdir(parents=True)

        report = doctor.build_report(self.reference, child, home=self.home, env={}, harnesses=('codex',))

        self.assertEqual(report['harnesses']['codex']['candidates'], [str(installed)])
        self.assertNotIn(str(outside), report['installations'])

    def test_report_is_deterministic_and_does_not_write_files(self):
        self.install(self.home / '.agents/skills/explain')
        self.defaults('User preference.\n\n' + self.block(self.core))

        def snapshot():
            result = {}
            for path in sorted(self.base.rglob('*')):
                kind = 'directory' if path.is_dir() else 'file'
                result[str(path.relative_to(self.base))] = (
                    kind, path.stat().st_mtime_ns, None if path.is_dir() else path.read_bytes())
            return result

        before = snapshot()
        first = self.report(harnesses=doctor.HARNESSES)
        second = self.report(harnesses=doctor.HARNESSES)

        self.assertEqual(first, second)
        self.assertEqual(before, snapshot())
        self.assertNotIn('cloud-installation.json', snapshot())

    def test_json_cli_exit_codes_distinguish_findings_from_input_errors(self):
        installed = self.install(self.home / '.agents/skills/explain')
        command = [sys.executable, '-B', str(SCRIPT), '--reference', str(self.reference),
                   '--project', str(self.project), '--harness', 'codex', '--json']

        success = subprocess.run(command, env={'HOME': str(self.home)}, capture_output=True, text=True)
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertTrue(json.loads(success.stdout)['ok'])

        self.write(installed / 'CORE.md', 'A changed rule.\n')
        difference = subprocess.run(command, env={'HOME': str(self.home)}, capture_output=True, text=True)
        self.assertEqual(difference.returncode, 1, difference.stderr)
        self.assertIn('installation_different', self.codes(json.loads(difference.stdout)))

        invalid = subprocess.run(command + ['--reference', str(self.base / 'missing-reference')],
                                 env={'HOME': str(self.home)}, capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn('reference must contain SKILL.md', invalid.stderr)
        self.assertEqual(invalid.stdout, '')

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'Named pipes require os.mkfifo')
    def test_named_pipes_do_not_block_default_manifest_or_skill_inspection(self):
        installed = self.install(self.home / '.agents/skills/explain')
        defaults = self.home / '.codex/AGENTS.md'
        manifest = installed / 'scripts/diagrams/package.json'
        unrelated = self.home / '.agents/skills/unrelated/SKILL.md'
        for path in (defaults, manifest, unrelated):
            path.parent.mkdir(parents=True, exist_ok=True)
            os.mkfifo(path)
        command = [sys.executable, '-B', str(SCRIPT), '--reference', str(self.reference),
                   '--project', str(self.project), '--harness', 'codex', '--json']

        result = subprocess.run(command, env={'HOME': str(self.home)}, capture_output=True,
                                text=True, timeout=5)

        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(self.global_defaults(report)['state'], 'unreadable')
        self.assertIn('defaults_unreadable', self.codes(report))
        installation = report['installations'][str(installed)]
        self.assertEqual(installation['state'], 'unreadable')
        self.assertIsNone(installation['pele'])
        self.assertEqual([item['file'] for item in installation['errors']],
                         ['scripts/diagrams/package.json'])
        self.assertEqual(report['harnesses']['codex']['candidates'], [str(installed)])


if __name__ == '__main__':
    unittest.main()
