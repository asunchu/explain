"""Keep interrupted and adversarial installation checks inside temporary homes."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
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


ROOT = Path(__file__).resolve().parents[1]
BUNDLED = ROOT / 'skills/explain/scripts'
sys.path.insert(0, str(BUNDLED))
import explain_doctor as doctor
import explain_repair as repair


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


installer = load_module('explain_adversarial_installer', ROOT / 'scripts/install.py')
runtime = load_module('explain_adversarial_runtime', ROOT / 'scripts/install_runtime.py')


class AdversarialInstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.repo = self.base / 'repo'
        self.source = self.repo / 'skills/explain'
        self.home = self.base / 'home'
        self.home.mkdir()
        self.backups = self.base / 'backups'
        self.env = {'SHELL': '/bin/bash'}
        self.write(self.source / 'SKILL.md', '---\nname: explain\n---\nExplain the topic.\n')
        self.write(self.source / 'CORE.md', '# Explain core\n\nPreserve meaning.\n')
        self.write(self.source / 'references/guide.md', 'Read the source.\n')
        self.write(self.source / 'scripts/explain', '#!/bin/sh\nprintf "Explain fixture\\n"\n')
        (self.source / 'scripts/explain').chmod(0o755)
        self.write(self.source / 'scripts/diagrams/render.mjs', '// Fixture renderer.\n')

    @staticmethod
    def write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)

    def installation_plan(self, runtime_info=None, core_only=True, env=None):
        plan = installer.make_plan(self.repo, self.home, self.env if env is None else env,
                                   runtime=runtime_info, core_only=core_only)
        self.assertEqual(plan.blockers, [])
        return plan

    def repair_plan(self):
        installed = self.home / '.agents/skills/explain'
        installed.parent.mkdir(parents=True)
        shutil.copytree(self.source, installed)
        self.write(installed / 'CORE.md', 'An older core.\n')
        self.write(installed / 'references/guide.md', 'An older guide.\n')
        self.write(self.home / '.codex/AGENTS.md',
                   doctor.START + '\nAn older writing rule.\n' + doctor.END + '\n')
        report = doctor.build_report(self.source, self.home, home=self.home,
                                     env=self.env, harnesses=('codex',), global_only=True)
        plan = repair.build_plan(report)
        self.assertEqual(plan.blockers, [])
        self.assertGreaterEqual(len(plan.operations), 3)
        return plan

    def manifest(self, pattern):
        paths = list(self.backups.glob(pattern))
        self.assertEqual(len(paths), 1)
        return json.loads(paths[0].read_text())

    def assert_original(self, operation):
        if operation.before is None:
            self.assertFalse(operation.path.exists(), str(operation.path))
        else:
            self.assertEqual(operation.path.read_bytes(), operation.before)
            self.assertEqual(stat.S_IMODE(operation.path.stat().st_mode), operation.mode)

    def runtime_fixture(self):
        folder = self.base / 'runtime'
        modules = folder / 'diagrams/node_modules'
        self.write(modules / 'pele/package.json', '{"version":"fixture"}\n')
        python = folder / '.venv/bin/python'
        self.write(python, '#!/bin/sh\nexit 0\n')
        python.chmod(0o755)
        return {'id': 'fixture-runtime', 'root': str(folder),
                'video': str(folder / 'video'), 'diagrams': str(folder / 'diagrams'),
                'venv': str(folder / '.venv'), 'python': str(python),
                'models': str(folder / 'models'), 'browser': str(folder / 'browser'),
                'marker': str(folder / 'ready.json'), 'versions': {'python': '3.11.9'},
                'hashes': {'requirements.lock.txt': 'fixture-hash'}}

    def test_repair_keyboard_interrupt_after_one_write_rolls_back(self):
        plan = self.repair_plan()
        first, failing = plan.operations[:2]
        original = repair.atomic_write
        interrupted = False

        def interrupt(path, content, mode):
            nonlocal interrupted
            if path == failing.path and not interrupted:
                self.assertEqual(first.path.read_bytes(), first.after)
                interrupted = True
                raise KeyboardInterrupt('Injected interrupt after one repair write')
            return original(path, content, mode)

        with mock.patch.object(repair, 'atomic_write', side_effect=interrupt):
            with self.assertRaises((KeyboardInterrupt, RuntimeError)):
                repair.apply_plan(plan, self.backups)
        self.assertTrue(interrupted)
        for operation in plan.operations:
            self.assert_original(operation)
        self.assertEqual(self.manifest('*/manifest.json')['status'], 'rolled_back')

    def test_installer_keyboard_interrupt_after_one_write_rolls_back(self):
        plan = self.installation_plan()
        first, failing = plan.files.operations[:2]
        original = repair.atomic_write
        interrupted = False

        def interrupt(path, content, mode):
            nonlocal interrupted
            if path == failing.path and not interrupted:
                self.assertEqual(first.path.read_bytes(), first.after)
                interrupted = True
                raise KeyboardInterrupt('Injected interrupt after one install write')
            return original(path, content, mode)

        with mock.patch.object(repair, 'atomic_write', side_effect=interrupt):
            with self.assertRaises((KeyboardInterrupt, RuntimeError)):
                installer.apply_install(plan, self.backups)
        self.assertTrue(interrupted)
        for operation in plan.files.operations:
            self.assert_original(operation)
        for link in plan.links:
            self.assertEqual(installer.signature(link.path), link.before)
        self.assertEqual(self.manifest('install-*/manifest.json')['status'], 'rolled_back')

    def test_interrupt_after_atomic_replacement_tracks_the_inflight_file(self):
        for name in ('repair', 'installer'):
            with self.subTest(transaction=name):
                # Each case owns a separate home and backup directory.
                self.home = self.base / ('home-' + name)
                self.home.mkdir()
                self.backups = self.base / ('backups-' + name)
                plan = self.repair_plan() if name == 'repair' else self.installation_plan()
                operations = plan.operations if name == 'repair' else plan.files.operations
                first = operations[0]
                original = repair.atomic_write
                interrupted = False

                def interrupt(path, content, mode):
                    nonlocal interrupted
                    result = original(path, content, mode)
                    if path == first.path and not interrupted:
                        self.assertEqual(first.path.read_bytes(), first.after)
                        interrupted = True
                        raise KeyboardInterrupt('Injected interrupt after atomic replacement')
                    return result

                with mock.patch.object(repair, 'atomic_write', side_effect=interrupt):
                    with self.assertRaises((KeyboardInterrupt, RuntimeError)):
                        if name == 'repair':
                            repair.apply_plan(plan, self.backups)
                        else:
                            installer.apply_install(plan, self.backups)
                self.assertTrue(interrupted)
                for operation in operations:
                    self.assert_original(operation)
                pattern = '*/manifest.json' if name == 'repair' else 'install-*/manifest.json'
                self.assertEqual(self.manifest(pattern)['status'], 'rolled_back')

    def test_installer_keyboard_interrupt_after_one_alias_rolls_back_outer_transaction(self):
        plan = self.installation_plan()
        first, failing = plan.links[:2]
        original = Path.symlink_to
        interrupted = False

        def interrupt(path, target, *args, **kwargs):
            nonlocal interrupted
            if (not interrupted and path.parent == failing.destination.parent
                    and Path(target) == failing.target):
                self.assertEqual(first.destination.resolve(), first.target)
                interrupted = True
                raise KeyboardInterrupt('Injected interrupt after one installed alias')
            return original(path, target, *args, **kwargs)

        with mock.patch.object(Path, 'symlink_to', new=interrupt):
            with self.assertRaises((KeyboardInterrupt, RuntimeError)):
                installer.apply_install(plan, self.backups)
        self.assertTrue(interrupted)
        for operation in plan.files.operations:
            self.assert_original(operation)
        for link in plan.links:
            self.assertEqual(installer.signature(link.path), link.before)
        self.assertEqual(self.manifest('install-*/manifest.json')['status'], 'rolled_back')

    def test_inner_commit_is_acknowledged_before_apply_plan_returns(self):
        self.write(self.home / '.codex/AGENTS.md', '# Existing private instructions.\n')
        plan = self.installation_plan()
        original = installer.apply_plan
        interrupted = False

        def interrupt_after_commit(*args, **kwargs):
            nonlocal interrupted
            original(*args, **kwargs)
            for operation in plan.files.operations:
                self.assertEqual(operation.path.read_bytes(), operation.after)
            interrupted = True
            raise KeyboardInterrupt('Injected interrupt between inner commit and return')

        with mock.patch.object(installer, 'apply_plan', side_effect=interrupt_after_commit):
            with self.assertRaises((KeyboardInterrupt, RuntimeError)):
                installer.apply_install(plan, self.backups)
        self.assertTrue(interrupted)
        for operation in plan.files.operations:
            self.assert_original(operation)
        for link in plan.links:
            self.assertEqual(installer.signature(link.path), link.before)
        manifest = self.manifest('install-*/manifest.json')
        self.assertEqual(manifest['status'], 'rolled_back')
        self.assertIsNotNone(manifest['regular_files'])
        regular_manifest = Path(manifest['regular_files']) / 'manifest.json'
        self.assertTrue(regular_manifest.is_file())
        records = json.loads(regular_manifest.read_text())['files']
        self.assertEqual({record['path'] for record in records},
                         {str(operation.path) for operation in plan.files.operations})

    def test_repair_preserves_external_edit_and_reports_incomplete_rollback(self):
        plan = self.repair_plan()
        first, owned, failing = plan.operations[:3]
        external = b'A concurrent user edit must survive.\n'
        original = repair.atomic_write
        injected = False

        def fail(path, content, mode):
            nonlocal injected
            if path == failing.path and not injected:
                self.assertEqual(first.path.read_bytes(), first.after)
                self.assertEqual(owned.path.read_bytes(), owned.after)
                first.path.write_bytes(external)
                injected = True
                raise OSError('Injected failure after external edit')
            return original(path, content, mode)

        with mock.patch.object(repair, 'atomic_write', side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, 'rollback_failed'):
                repair.apply_plan(plan, self.backups)
        self.assertTrue(injected)
        self.assertEqual(first.path.read_bytes(), external)
        for operation in plan.operations[1:]:
            self.assert_original(operation)
        manifest = self.manifest('*/manifest.json')
        self.assertEqual(manifest['status'], 'rollback_failed')
        self.assertTrue(manifest['rollback_errors'])

    def test_installer_preserves_external_edit_and_restores_owned_files(self):
        plan = self.installation_plan()
        first = plan.files.operations[0]
        external = b'A concurrent user edit must survive.\n'
        original = Path.symlink_to
        injected = False

        def fail(path, target, *args, **kwargs):
            nonlocal injected
            if not injected:
                self.assertEqual(first.path.read_bytes(), first.after)
                first.path.write_bytes(external)
                injected = True
                raise OSError('Injected link failure after external edit')
            return original(path, target, *args, **kwargs)

        with mock.patch.object(Path, 'symlink_to', new=fail):
            with self.assertRaisesRegex(RuntimeError, 'rollback_failed'):
                installer.apply_install(plan, self.backups)
        self.assertTrue(injected)
        self.assertEqual(first.path.read_bytes(), external)
        for operation in plan.files.operations[1:]:
            self.assert_original(operation)
        manifest = self.manifest('install-*/manifest.json')
        self.assertEqual(manifest['status'], 'rollback_failed')
        self.assertTrue(manifest['rollback_errors'])

    def test_installer_preserves_external_alias_and_removes_owned_aliases(self):
        plan = self.installation_plan()
        self.assertGreaterEqual(len(plan.links), 3)
        first, owned, failing = plan.links[:3]
        external = self.base / 'external-skill'
        external.mkdir()
        original = Path.symlink_to
        injected = False

        def fail(path, target, *args, **kwargs):
            nonlocal injected
            if (not injected and path.parent == failing.destination.parent
                    and Path(target) == failing.target):
                self.assertTrue(first.destination.is_symlink())
                self.assertTrue(owned.destination.is_symlink())
                first.destination.unlink()
                original(first.destination, external, target_is_directory=True)
                injected = True
                raise OSError('Injected failure after external alias replacement')
            return original(path, target, *args, **kwargs)

        with mock.patch.object(Path, 'symlink_to', new=fail):
            with self.assertRaisesRegex(RuntimeError, 'rollback_failed'):
                installer.apply_install(plan, self.backups)
        self.assertTrue(injected)
        self.assertEqual(os.readlink(first.destination), str(external))
        self.assertEqual(installer.signature(owned.destination), owned.before)
        for operation in plan.files.operations:
            self.assert_original(operation)
        manifest = self.manifest('install-*/manifest.json')
        self.assertEqual(manifest['status'], 'rollback_failed')
        self.assertTrue(manifest['rollback_errors'])

    def test_unready_runtime_nested_symlinks_never_overwrite_external_files(self):
        tools = {'paths': {'npm': 'fixture-npm', 'python': 'fixture-python'},
                 'platform': {'system': 'fixture', 'machine': 'fixture'}, 'versions': {}}
        identifier, _ = runtime._identity(ROOT, tools)
        for relative in ('video/package.json', 'video/runtime-smoke.jsx'):
            with self.subTest(relative=relative):
                base = self.base / relative.replace('/', '-')
                canonical = base / identifier
                outside = self.base / ('outside-' + relative.replace('/', '-'))
                before = b'External user bytes must survive.\n'
                self.write(outside, before)
                alias = canonical / relative
                alias.parent.mkdir(parents=True)
                alias.symlink_to(outside)
                with mock.patch.object(runtime, '_host_tools', return_value=tools), \
                        mock.patch.object(runtime, '_run', side_effect=runtime.RuntimeInstallError('Offline stop before npm')) as command, \
                        mock.patch.object(runtime, 'urlopen', side_effect=AssertionError('Unexpected network')):
                    with self.assertRaisesRegex(runtime.RuntimeInstallError, 'Offline stop before npm'):
                        runtime.prepare_runtime(ROOT, base)
                self.assertEqual(outside.read_bytes(), before)
                self.assertTrue(alias.is_symlink())
                self.assertEqual(os.readlink(alias), str(outside))
                self.assertEqual(command.call_count, 1)
                self.assertNotEqual(command.call_args.kwargs['cwd'].parent, canonical)
                self.assertEqual(list(base.rglob('ready.json')), [])

    def test_regular_read_only_doctor_does_not_create_installed_bytecode(self):
        for path in BUNDLED.glob('*.py'):
            self.write(self.source / 'scripts' / path.name, path.read_bytes())
        self.write(self.source / 'scripts/explain', (BUNDLED / 'explain').read_bytes())
        plan = self.installation_plan()
        installer.apply_install(plan, self.backups)
        before = {str(path.relative_to(plan.target)): path.read_bytes()
                  for path in plan.target.rglob('*') if path.is_file()}
        self.assertFalse(list(plan.target.rglob('__pycache__')))
        environment = {'HOME': str(self.home), 'PATH': '/usr/bin:/bin', 'SHELL': '/bin/bash',
                       'CODEX_HOME': str(self.home / '.codex'),
                       'CLAUDE_CONFIG_DIR': str(self.home / '.claude'),
                       'XDG_CONFIG_HOME': str(self.home / '.config'),
                       'XDG_STATE_HOME': str(self.home / '.local/state')}
        self.assertNotIn('PYTHONDONTWRITEBYTECODE', environment)
        result = subprocess.run(
            [sys.executable, str(plan.target / 'scripts/explain'), 'doctor', '--json', '--global-only'],
            cwd=self.base, env=environment, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertTrue(json.loads(result.stdout)['ok'])
        self.assertFalse(list(plan.target.rglob('__pycache__')))
        after = {str(path.relative_to(plan.target)): path.read_bytes()
                 for path in plan.target.rglob('*') if path.is_file()}
        self.assertEqual(after, before)

    def test_ordinary_installer_dry_run_does_not_write_checkout_bytecode(self):
        script = self.repo / 'scripts/install.py'
        self.write(script, (ROOT / 'scripts/install.py').read_bytes())
        for path in BUNDLED.glob('*.py'):
            self.write(self.source / 'scripts' / path.name, path.read_bytes())
        before = {str(path.relative_to(self.repo)): path.read_bytes()
                  for path in self.repo.rglob('*') if path.is_file()}
        environment = {'HOME': str(self.home), 'PATH': '/usr/bin:/bin', 'SHELL': '/bin/bash',
                       'CODEX_HOME': str(self.home / '.codex'),
                       'CLAUDE_CONFIG_DIR': str(self.home / '.claude'),
                       'XDG_CONFIG_HOME': str(self.home / '.config'),
                       'XDG_STATE_HOME': str(self.home / '.local/state')}
        self.assertNotIn('PYTHONDONTWRITEBYTECODE', environment)
        result = subprocess.run([sys.executable, str(script), '--core-only', '--dry-run'],
                                cwd=self.base, env=environment, capture_output=True,
                                text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(json.loads(result.stdout)['status'], 'dry_run')
        self.assertFalse(list(self.repo.rglob('__pycache__')))
        self.assertEqual(list(self.home.iterdir()), [])
        after = {str(path.relative_to(self.repo)): path.read_bytes()
                 for path in self.repo.rglob('*') if path.is_file()}
        self.assertEqual(after, before)

    def test_post_activation_check_failure_reports_active_state_and_backup(self):
        original = installer.build_report
        calls = 0
        output, errors = io.StringIO(), io.StringIO()

        def fail_final_check(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError('Injected post-activation verification failure')
            return original(*args, **kwargs)

        with mock.patch.object(installer, 'ROOT', self.repo), \
                mock.patch.object(installer.Path, 'home', return_value=self.home), \
                mock.patch.dict(os.environ, self.env, clear=True), \
                mock.patch.object(installer, 'build_report', side_effect=fail_final_check), \
                redirect_stdout(output), redirect_stderr(errors):
            status = installer.main(['--core-only'])
        self.assertEqual(status, 2)
        self.assertEqual(calls, 3)
        backups = list((self.home / '.local/state/explain/backups').glob('install-*'))
        self.assertEqual(len(backups), 1)
        reported = output.getvalue() + errors.getvalue()
        self.assertIn('Injected post-activation verification failure', reported)
        self.assertIn('Configuration status: applied', reported)
        self.assertIn(str(backups[0]), reported)
        self.assertEqual(json.loads((backups[0] / 'manifest.json').read_text())['status'], 'applied')
        self.assertTrue((self.home / '.local/bin/explain').is_symlink())
        report = doctor.build_report(self.source, self.home, home=self.home, env=self.env,
                                     global_only=True)
        self.assertTrue(report['ok'], report['findings'])

    def test_zsh_profiles_follow_zdotdir(self):
        zdotdir = self.home / 'shell-config'
        for name in ('.zshrc', '.zprofile'):
            self.write(zdotdir / name, '# Existing ZDOTDIR profile.\n')
            self.write(self.home / name, '# Unused home profile.\n')
        plan = self.installation_plan(env={'SHELL': '/bin/zsh', 'ZDOTDIR': str(zdotdir)})
        installer.apply_install(plan, self.backups)
        for name in ('.zshrc', '.zprofile'):
            self.assertIn('# explain-path:start', (zdotdir / name).read_text())
            self.assertEqual((self.home / name).read_text(), '# Unused home profile.\n')

    def test_codex_nonempty_global_override_receives_effective_defaults(self):
        override = self.home / '.codex/AGENTS.override.md'
        ignored = self.home / '.codex/AGENTS.md'
        prefix = '# Existing effective override.\n'
        self.write(override, prefix)
        self.write(ignored, '# Lower priority global instructions.\n')
        plan = self.installation_plan()
        installer.apply_install(plan, self.backups)
        self.assertTrue(override.read_text().startswith(prefix))
        self.assertIn(doctor.START, override.read_text())
        self.assertIn((self.source / 'CORE.md').read_text().strip(), override.read_text())
        self.assertEqual(ignored.read_text(), '# Lower priority global instructions.\n')
        report = doctor.build_report(self.source, self.home, home=self.home, env=self.env,
                                     harnesses=('codex',), global_only=True)
        self.assertTrue(report['ok'], report['findings'])
        self.assertIn(str(override), [item['path'] for item in report['harnesses']['codex']['defaults']])

    def test_configuration_inside_installation_is_blocked_before_writes(self):
        target = self.home / '.agents/skills/explain'
        before = list(self.home.rglob('*'))
        plan = installer.make_plan(self.repo, self.home,
                                   {'SHELL': '/bin/bash', 'CODEX_HOME': str(target)},
                                   core_only=True)
        self.assertTrue(plan.blockers)
        self.assertEqual(list(self.home.rglob('*')), before)
        with self.assertRaises(ValueError):
            installer.apply_install(plan, self.backups)
        self.assertEqual(list(self.home.rglob('*')), before)
        self.assertFalse(self.backups.exists())

    def test_bash_login_precedes_profile_when_bash_profile_is_absent(self):
        self.write(self.home / '.bash_login', '# Existing Bash login.\n')
        self.write(self.home / '.profile', '# Lower priority login profile.\n')
        plan = self.installation_plan()
        installer.apply_install(plan, self.backups)
        self.assertIn('# explain-path:start', (self.home / '.bash_login').read_text())
        self.assertEqual((self.home / '.profile').read_text(), '# Lower priority login profile.\n')
        self.assertFalse((self.home / '.bash_profile').exists())

    def test_profile_preserves_python_and_pip_selection_without_private_venv_on_path(self):
        runtime_info = self.runtime_fixture()
        existing = self.base / 'existing-tools'
        for name in ('python3', 'pip', 'pip3'):
            self.write(existing / name, '#!/bin/sh\nexit 0\n')
            (existing / name).chmod(0o755)
            private = Path(runtime_info['python']).parent / name
            self.write(private, '#!/bin/sh\nexit 0\n')
            private.chmod(0o755)
        initial = str(existing) + ':/usr/bin:/bin'
        plan = self.installation_plan(runtime_info, core_only=False)
        installer.apply_install(plan, self.backups)
        for name in ('.bashrc', '.profile'):
            with self.subTest(profile=name):
                result = subprocess.run(
                    ['/bin/bash', '-c', '. "$1"; . "$1"; printf "%s\\n" "$PATH"; command -v python3; command -v pip; command -v pip3',
                     'explain-profile-test', str(self.home / name)],
                    env={'HOME': str(self.home), 'PATH': initial}, capture_output=True,
                    text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                paths, *selected = result.stdout.splitlines()
                self.assertNotIn(str(Path(runtime_info['python']).parent), paths.split(':'))
                self.assertEqual(selected, [str(existing / item) for item in ('python3', 'pip', 'pip3')])
                self.assertEqual(paths.split(':').count(str(self.home / '.local/bin')), 1)
                self.assertEqual([item for item in paths.split(':') if item != str(self.home / '.local/bin')],
                                 initial.split(':'))

    def test_core_only_rerun_retains_full_runtime_receipt_and_dependency_link(self):
        runtime_info = self.runtime_fixture()
        plan = self.installation_plan(runtime_info, core_only=False)
        installer.apply_install(plan, self.backups)
        receipt = self.home / '.local/state/explain/toolchain.json'
        before = json.loads(receipt.read_text())
        modules = plan.target / 'scripts/diagrams/node_modules'
        dependency_target = os.readlink(modules)
        rerun = self.installation_plan(core_only=True)
        installer.apply_install(rerun, self.backups)
        self.assertEqual(json.loads(receipt.read_text()), before)
        self.assertFalse(before['core_only'])
        self.assertEqual(before['runtime']['id'], runtime_info['id'])
        self.assertTrue(modules.is_symlink())
        self.assertEqual(os.readlink(modules), dependency_target)
        self.assertEqual(modules.resolve(), Path(runtime_info['diagrams']) / 'node_modules')

    def test_archive_license_notices_are_owned_payload_during_upgrade(self):
        installed = self.home / '.agents/skills/explain'
        installed.parent.mkdir(parents=True)
        shutil.copytree(self.source, installed)
        notices = {}
        for name in ('LICENSE', 'THIRD_PARTY.md'):
            shipped = ROOT / 'skills/explain' / name
            self.assertTrue(shipped.is_file(), str(shipped))
            notices[name] = shipped.read_bytes()
            self.write(self.source / name, notices[name])
            self.write(installed / name, notices[name])
        self.write(installed / 'CORE.md', 'An older installed core.\n')
        plan = self.installation_plan()
        self.assertEqual(plan.target, installed)
        self.assertEqual(installer.apply_install(plan, self.backups)['status'], 'applied')
        for name, expected in notices.items():
            self.assertEqual((installed / name).read_bytes(), expected)
        report = doctor.build_report(self.source, self.home, home=self.home, env=self.env,
                                     global_only=True)
        self.assertTrue(report['ok'], report['findings'])


if __name__ == '__main__':
    unittest.main()
