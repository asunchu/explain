import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/doctor.py'
sys.path.insert(0, str(SCRIPT.parent))
import doctor
import doctor_repair as repair


class DoctorRepairTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.reference = self.base / 'reference'
        self.home = self.base / 'home'
        self.project = self.base / 'project'
        self.backups = self.base / 'backups'
        for directory in (self.reference, self.home, self.project):
            directory.mkdir()
        (self.project / '.git').mkdir()
        self.core = '# Explain core\n\nPreserve meaning.\n'
        self.write(self.reference / 'SKILL.md', '---\nname: explain\n---\nExplain the topic.\n')
        self.write(self.reference / 'CORE.md', self.core)
        self.write(self.reference / 'references/guide.md', 'Read the source.\n')

    @staticmethod
    def write(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)

    def install(self, path=None):
        path = path or self.home / '.agents/skills/explain'
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.reference, path)
        return path

    def block(self, content=None):
        return (doctor.START + '\n' + (self.core if content is None else content).strip()
                + '\n' + doctor.END + '\n')

    def defaults(self, content=None, path=None):
        path = path or self.home / '.codex/AGENTS.md'
        self.write(path, self.block('An older writing rule.') if content is None else content)
        return path

    def report(self, harnesses=('codex',), env=None):
        return doctor.build_report(self.reference, self.project, home=self.home,
                                   env={} if env is None else env, harnesses=harnesses)

    def plan(self, harnesses=('codex',), env=None):
        return repair.build_plan(self.report(harnesses, env))

    def snapshot(self):
        result = {}
        for path in sorted(self.base.rglob('*')):
            info = path.lstat()
            content = (os.readlink(path) if path.is_symlink() else None if path.is_dir()
                       else path.read_bytes())
            result[str(path.relative_to(self.base))] = (info.st_mode, info.st_mtime_ns, content)
        return result

    def cli(self, *arguments, env=None):
        command = [sys.executable, '-B', str(SCRIPT), '--reference', str(self.reference),
                   '--project', str(self.project), '--harness', 'codex', '--json', *arguments]
        return subprocess.run(command, env={'HOME': str(self.home), **(env or {})},
                              capture_output=True, text=True, timeout=10)

    @staticmethod
    def digest(data):
        return hashlib.sha256(data).hexdigest() if data is not None else None

    def test_shared_three_harness_aliases_repair_each_file_once_and_preserve_dependencies(self):
        installed = self.install()
        aliases = [self.home / name / 'skills/explain'
                   for name in ('.codex', '.claude', '.config/opencode')]
        for alias in aliases:
            alias.parent.mkdir(parents=True)
            alias.symlink_to(installed, target_is_directory=True)
        self.write(installed / 'CORE.md', 'An older core.\n')
        (installed / 'references/guide.md').unlink()
        dependencies = {}
        for directory in ('node_modules', '.venv', 'models', '__pycache__'):
            path = installed / directory / 'keep.bin'
            self.write(path, b'Locally installed dependency\x00\xff')
            dependencies[path] = path.read_bytes()
        defaults = [self.defaults(path=self.home / name / filename)
                    for name, filename in (('.codex', 'AGENTS.md'),
                                           ('.claude', 'CLAUDE.md'),
                                           ('.config/opencode', 'AGENTS.md'))]

        plan = self.plan(doctor.HARNESSES)

        self.assertEqual(plan.blockers, [])
        self.assertEqual(len(plan.installations), 1)
        self.assertEqual(set(plan.aliases), {installed, *aliases})
        paths = [operation.path for operation in plan.operations]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(set(paths), {installed / 'CORE.md', installed / 'references/guide.md', *defaults})
        result = repair.apply_plan(plan, self.backups)
        self.assertEqual(result['changed_files'], 5)
        self.assertTrue(self.report(doctor.HARNESSES)['ok'])
        for alias in aliases:
            self.assertTrue(alias.is_symlink())
            self.assertEqual(alias.resolve(), installed)
        for path, content in dependencies.items():
            self.assertEqual(path.read_bytes(), content)

    def test_backups_preserve_original_bytes_with_private_modes_and_a_complete_manifest(self):
        installed = self.install()
        self.write(installed / 'CORE.md', 'A private local rule.\n')
        (installed / 'CORE.md').chmod(0o640)
        (installed / 'references/guide.md').unlink()
        defaults = self.defaults()
        defaults.chmod(0o600)
        plan = self.plan()
        before = {operation.path: operation.before for operation in plan.operations}

        result = repair.apply_plan(plan, self.backups)

        self.assertEqual(result['status'], 'applied')
        backup = Path(result['backup_directory'])
        for directory in (self.backups, backup, backup / 'files'):
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        manifest_path = backup / 'manifest.json'
        self.assertEqual(stat.S_IMODE(manifest_path.stat().st_mode), 0o600)
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest['schema_version'], 1)
        self.assertEqual(manifest['status'], 'applied')
        self.assertEqual(manifest['plan'], plan.summary())
        self.assertEqual({Path(record['path']) for record in manifest['files']}, set(before))
        for record in manifest['files']:
            path = Path(record['path'])
            self.assertEqual(record['before_sha256'], self.digest(before[path]))
            self.assertEqual(record['after_sha256'], self.digest(path.read_bytes()))
            if before[path] is None:
                self.assertIsNone(record['backup_file'])
            else:
                saved = backup / record['backup_file']
                self.assertEqual(saved.read_bytes(), before[path])
                self.assertEqual(stat.S_IMODE(saved.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((installed / 'CORE.md').stat().st_mode), 0o640)
        self.assertEqual(stat.S_IMODE(defaults.stat().st_mode), 0o600)

    def test_crlf_defaults_keep_outside_bytes_and_the_symlink_alias(self):
        installed = self.install()
        target = self.base / 'private/instructions.md'
        prefix = '# User café instructions\r\n\r\n'.encode()
        suffix = b'\r\n\r\n## Keep this section\r\nLeave this exact text.\r\n'
        before = (prefix + doctor.START.encode() + b'\r\nAn older writing rule.\r\n'
                  + doctor.END.encode() + suffix)
        self.write(target, before)
        target.chmod(0o640)
        alias = self.home / '.codex/AGENTS.md'
        alias.parent.mkdir(parents=True)
        alias.symlink_to(target)

        plan = self.plan()
        self.assertEqual(len(plan.operations), 1)
        self.assertEqual(plan.operations[0].path, target)
        self.assertEqual(plan.operations[0].input_path, alias)
        repair.apply_plan(plan, self.backups)

        after = target.read_bytes()
        self.assertEqual(after.split(doctor.START.encode(), 1)[0], prefix)
        self.assertEqual(after.split(doctor.END.encode(), 1)[1], suffix)
        block = after.split(doctor.START.encode(), 1)[1].split(doctor.END.encode(), 1)[0]
        self.assertNotIn(b'\n', block.replace(b'\r\n', b''))
        self.assertIn(self.core.strip().replace('\n', '\r\n').encode(), block)
        self.assertIn(str(installed / 'SKILL.md').encode(), block)
        self.assertTrue(alias.is_symlink())
        self.assertEqual(os.readlink(alias), str(target))
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)
        self.assertTrue(self.report()['ok'])

    def test_replace_block_rejects_incomplete_reversed_and_duplicate_markers(self):
        for content in (doctor.START, doctor.END, doctor.END + doctor.START,
                        self.block() + self.block()):
            with self.subTest(content=content):
                with self.assertRaises(ValueError):
                    repair.replace_block(content.encode(), self.core, self.base / 'installation')

    def test_dry_run_reports_actions_without_writes_or_backups(self):
        installed = self.install()
        self.write(installed / 'CORE.md', 'An older core.\n')
        self.defaults()
        before = self.snapshot()

        result = self.cli('--fix', '--dry-run', '--backup-dir', str(self.backups))

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report['ok'])
        self.assertEqual(report['repair']['status'], 'dry_run')
        self.assertEqual(len(report['repair']['plan']['actions']), 2)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.backups.exists())
        self.assertFalse((self.home / '.local/state').exists())

    def test_failure_after_one_write_restores_original_contents_and_modes(self):
        installed = self.install()
        self.write(installed / 'CORE.md', 'A core to restore.\n')
        (installed / 'CORE.md').chmod(0o640)
        defaults = self.defaults()
        defaults.chmod(0o600)
        plan = self.plan()
        self.assertEqual(len(plan.operations), 2)
        first, failing = plan.operations
        failed = False
        original_write = repair.atomic_write

        def fail_once(path, content, mode):
            nonlocal failed
            if path == failing.path and not failed:
                self.assertEqual(first.path.read_bytes(), first.after)
                failed = True
                raise OSError('Injected destination failure')
            return original_write(path, content, mode)

        with mock.patch.object(repair, 'atomic_write', side_effect=fail_once):
            with self.assertRaisesRegex(RuntimeError, 'Status: rolled_back'):
                repair.apply_plan(plan, self.backups)

        self.assertTrue(failed)
        for operation in plan.operations:
            self.assertEqual(operation.path.read_bytes(), operation.before)
            self.assertEqual(stat.S_IMODE(operation.path.stat().st_mode), operation.mode)
        manifests = list(self.backups.glob('*/manifest.json'))
        self.assertEqual(len(manifests), 1)
        manifest = json.loads(manifests[0].read_text())
        self.assertEqual(manifest['status'], 'rolled_back')
        self.assertEqual(manifest['rollback_errors'], [])
        self.assertIn('Injected destination failure', manifest['error'])

    def test_failure_after_creating_a_file_removes_it_and_its_new_parent_directories(self):
        self.write(self.reference / 'a-new/nested/rule.md', 'A new package rule.\n')
        installed = self.install()
        shutil.rmtree(installed / 'a-new')
        self.write(installed / 'references/guide.md', 'An older guide.\n')
        plan = self.plan()
        first, failing = plan.operations
        self.assertIsNone(first.before)
        self.assertEqual(first.path, installed / 'a-new/nested/rule.md')
        failed = False
        original_write = repair.atomic_write

        def fail_once(path, content, mode):
            nonlocal failed
            if path == failing.path and not failed:
                self.assertEqual(first.path.read_bytes(), first.after)
                failed = True
                raise OSError('Injected failure after creation')
            return original_write(path, content, mode)

        with mock.patch.object(repair, 'atomic_write', side_effect=fail_once):
            with self.assertRaisesRegex(RuntimeError, 'Status: rolled_back'):
                repair.apply_plan(plan, self.backups)

        self.assertTrue(failed)
        self.assertFalse((installed / 'a-new').exists())
        self.assertEqual(failing.path.read_bytes(), failing.before)
        manifest = json.loads(next(self.backups.glob('*/manifest.json')).read_text())
        created_record = next(item for item in manifest['files'] if item['path'] == str(first.path))
        self.assertIsNone(created_record['backup_file'])
        self.assertIsNone(created_record['before_sha256'])
        self.assertEqual(manifest['status'], 'rolled_back')

    def test_stale_reference_installation_and_defaults_abort_before_backup_or_write(self):
        installed = self.install()
        self.write(installed / 'CORE.md', 'An older core.\n')
        defaults = self.defaults()
        paths = {'reference': self.reference / 'CORE.md', 'installation': installed / 'CORE.md',
                 'defaults': defaults}
        for name, path in paths.items():
            with self.subTest(changed=name):
                original = path.read_bytes()
                plan = self.plan()
                self.assertEqual(plan.blockers, [])
                self.write(path, original + b'Changed after planning.\n')
                before = self.snapshot()
                backup = self.base / ('stale-' + name)
                with self.assertRaisesRegex(ValueError, 'changed after planning'):
                    repair.apply_plan(plan, backup)
                self.assertEqual(before, self.snapshot())
                self.assertFalse(backup.exists())
                path.write_bytes(original)

    def test_reference_changed_since_report_blocks_planning(self):
        self.install()
        report = self.report()
        self.write(self.reference / 'CORE.md', 'Changed after reporting.\n')

        plan = repair.build_plan(report)

        self.assertTrue(plan.blockers)
        self.assertEqual(plan.operations, [])
        with self.assertRaisesRegex(ValueError, 'Repair is blocked'):
            repair.apply_plan(plan, self.backups)
        self.assertFalse(self.backups.exists())

    def test_non_directory_parent_blocks_repairs_before_backup_or_write(self):
        installed = self.install()
        shutil.rmtree(installed / 'references')
        self.write(installed / 'references', 'A local file occupies the required directory.\n')
        self.write(installed / 'CORE.md', 'An older core.\n')
        plan = self.plan()
        before = self.snapshot()

        self.assertTrue(any('parent is not a directory' in item for item in plan.blockers))
        with self.assertRaisesRegex(ValueError, 'Repair is blocked'):
            repair.apply_plan(plan, self.backups)

        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.backups.exists())

    def test_missing_package_file_keeps_the_reference_executable_mode(self):
        source = self.reference / 'scripts/helper.py'
        self.write(source, '#!/usr/bin/env python3\nprint("Explain")\n')
        source.chmod(0o755)
        installed = self.install()
        destination = installed / 'scripts/helper.py'
        destination.unlink()
        plan = self.plan()

        self.assertEqual(len(plan.operations), 1)
        self.assertEqual(plan.operations[0].mode, 0o755)
        repair.apply_plan(plan, self.backups)

        self.assertEqual(destination.read_bytes(), source.read_bytes())
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o755)

    def test_concurrent_later_default_change_rolls_back_the_package_and_preserves_the_external_edit(self):
        installed = self.install()
        self.write(installed / 'CORE.md', 'A core to restore.\n')
        defaults = self.defaults()
        plan = self.plan()
        first, later = plan.operations
        self.assertEqual(first.kind, 'skill')
        self.assertEqual(later.path, defaults)
        external = b'A concurrent user edit replaces this defaults file.\n'
        edited = False
        original_write = repair.atomic_write

        def edit_later_default(path, content, mode):
            nonlocal edited
            result = original_write(path, content, mode)
            if path == first.path and content == first.after and not edited:
                defaults.write_bytes(external)
                edited = True
            return result

        with mock.patch.object(repair, 'atomic_write', side_effect=edit_later_default):
            with self.assertRaisesRegex(RuntimeError, 'Destination changed after planning'):
                repair.apply_plan(plan, self.backups)

        self.assertTrue(edited)
        self.assertEqual(first.path.read_bytes(), first.before)
        self.assertEqual(defaults.read_bytes(), external)
        manifest = json.loads(next(self.backups.glob('*/manifest.json')).read_text())
        self.assertEqual(manifest['status'], 'rolled_back')
        self.assertEqual(manifest['rollback_errors'], [])

    def test_retargeted_default_symlink_aborts_before_backup_or_write(self):
        self.install()
        first = self.base / 'instructions-one.md'
        second = self.base / 'instructions-two.md'
        self.write(first, self.block('An older rule.'))
        self.write(second, first.read_bytes())
        alias = self.home / '.codex/AGENTS.md'
        alias.parent.mkdir(parents=True)
        alias.symlink_to(first)
        plan = self.plan()
        alias.unlink()
        alias.symlink_to(second)
        before = self.snapshot()

        with self.assertRaisesRegex(ValueError, 'Destination path changed after planning'):
            repair.apply_plan(plan, self.backups)

        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.backups.exists())

    def test_ambiguous_copies_block_all_repairs(self):
        installed = self.install()
        self.install(self.home / '.codex/skills/explain')
        self.write(installed / 'CORE.md', 'An older core.\n')
        self.defaults()
        plan = self.plan()
        before = self.snapshot()

        self.assertTrue(plan.blockers)
        self.assertTrue(any('multiple_copies' in item for item in plan.blockers))
        with self.assertRaisesRegex(ValueError, 'Repair is blocked'):
            repair.apply_plan(plan, self.backups)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.backups.exists())

    def test_invalid_default_markers_block_package_repairs(self):
        installed = self.install()
        self.write(installed / 'CORE.md', 'An older core.\n')
        defaults = self.defaults()
        for content in (doctor.START + '\nAn unfinished rule.\n',
                        doctor.END + '\n' + doctor.START, self.block() * 2):
            with self.subTest(content=content):
                defaults.write_text(content)
                plan = self.plan()
                before = self.snapshot()
                self.assertTrue(any('defaults_invalid_markers' in item for item in plan.blockers))
                with self.assertRaisesRegex(ValueError, 'Repair is blocked'):
                    repair.apply_plan(plan, self.backups)
                self.assertEqual(before, self.snapshot())
                self.assertFalse(self.backups.exists())

    def test_conflicting_harness_routes_to_one_default_file_block_all_repairs(self):
        codex = self.install(self.home / '.codex/skills/explain')
        opencode = self.install(self.home / '.config/opencode/skills/explain')
        self.defaults(self.block(), self.project / 'AGENTS.md')

        plan = self.plan(('codex', 'opencode'))

        self.assertEqual(set(plan.installations), {codex, opencode})
        self.assertTrue(any('Conflicting repairs target the same file' in item for item in plan.blockers))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Repair is blocked'):
            repair.apply_plan(plan, self.backups)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.backups.exists())

    def test_extra_files_remain_unchanged_and_leave_residual_findings(self):
        installed = self.install()
        self.write(installed / 'CORE.md', 'An older core.\n')
        extra = installed / 'local-note.txt'
        self.write(extra, b'Preserve this local note.\x00\xff')
        plan = self.plan()

        self.assertEqual(plan.blockers, [])
        self.assertTrue(any('extra files remain unchanged' in item for item in plan.notes))
        repair.apply_plan(plan, self.backups)

        self.assertEqual(extra.read_bytes(), b'Preserve this local note.\x00\xff')
        report = self.report()
        self.assertFalse(report['ok'])
        self.assertEqual(report['installations'][str(installed)]['changed'], [])
        self.assertEqual(report['installations'][str(installed)]['extra'], ['local-note.txt'])
        self.assertEqual({item['code'] for item in report['findings']}, {'installation_different'})
        repeated = self.plan()
        self.assertEqual(repeated.operations, [])
        before = self.snapshot()
        self.assertEqual(repair.apply_plan(repeated, self.backups),
                         {'status': 'no_changes', 'backup_directory': None, 'changed_files': 0})
        self.assertEqual(before, self.snapshot())

    def test_cli_fix_uses_home_backup_defaults_and_repeated_fix_makes_no_changes(self):
        installed = self.install()
        self.write(installed / 'CORE.md', 'An older core.\n')
        self.defaults()

        result = self.cli('--fix')

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report['ok'])
        self.assertEqual(report['repair']['status'], 'applied')
        self.assertEqual(report['repair']['changed_files'], 2)
        backup = Path(report['repair']['backup_directory'])
        self.assertEqual(backup.parent, self.home / '.local/state/explain/backups')
        before = self.snapshot()
        repeated = self.cli('--fix')
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        repeated_report = json.loads(repeated.stdout)
        self.assertTrue(repeated_report['ok'])
        self.assertEqual(repeated_report['repair']['status'], 'no_changes')
        self.assertIsNone(repeated_report['repair']['backup_directory'])
        self.assertEqual(repeated_report['repair']['changed_files'], 0)
        self.assertEqual(before, self.snapshot())

    def test_cli_honors_custom_configuration_and_state_directories(self):
        config = self.base / 'custom-codex'
        state = self.base / 'custom-state'
        installed = self.install(config / 'skills/explain')
        self.write(installed / 'CORE.md', 'An older core.\n')
        self.defaults(path=config / 'AGENTS.md')

        result = self.cli('--fix', env={'CODEX_HOME': str(config), 'XDG_STATE_HOME': str(state)})

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report['ok'])
        self.assertEqual(report['harnesses']['codex']['candidates'], [str(installed)])
        self.assertEqual(Path(report['repair']['backup_directory']).parent, state / 'explain/backups')
        self.assertFalse((self.home / '.codex').exists())
        self.assertFalse((self.home / '.local').exists())

    def test_cli_fix_preserves_extras_and_returns_the_residual_finding_exit_code(self):
        installed = self.install()
        self.write(installed / 'CORE.md', 'An older core.\n')
        self.write(installed / 'local-note.txt', 'Keep this note.\n')

        result = self.cli('--fix', '--backup-dir', str(self.backups))

        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report['ok'])
        self.assertEqual(report['repair']['status'], 'applied')
        self.assertEqual(report['repair']['changed_files'], 1)
        self.assertEqual(Path(report['repair']['backup_directory']).parent, self.backups)
        self.assertEqual((installed / 'local-note.txt').read_text(), 'Keep this note.\n')

    def test_cli_blocked_fix_does_not_create_backups_or_write_files(self):
        self.install()
        self.install(self.home / '.codex/skills/explain')
        self.defaults()
        before = self.snapshot()

        result = self.cli('--fix', '--backup-dir', str(self.backups))

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)['repair']['status'], 'blocked')
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.backups.exists())

    def test_cli_requires_fix_for_dry_run_and_backup_options(self):
        for arguments in (('--dry-run',), ('--backup-dir', str(self.backups))):
            with self.subTest(arguments=arguments):
                result = self.cli(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertIn('requires --fix', result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertFalse(self.backups.exists())


if __name__ == '__main__':
    unittest.main()
