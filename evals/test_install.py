"""Exercise installation only inside temporary home and configuration directories."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/install.py'
SPEC = importlib.util.spec_from_file_location('explain_installer_tests', SCRIPT)
installer = importlib.util.module_from_spec(SPEC)
# Dataclasses resolve their declaring module while the module executes.
sys.modules[SPEC.name] = installer
SPEC.loader.exec_module(installer)
START = '<!-- explain-writing-default:start -->'
END = '<!-- explain-writing-default:end -->'


class InstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.repo = self.base / 'repo'
        self.source = self.repo / 'skills/explain'
        self.home = self.base / 'home'
        self.home.mkdir()
        self.backups = self.base / 'backups'
        self.env = {'SHELL': '/bin/zsh'}
        self.core = '# Explain core\n\nPreserve meaning before shortening.\n'
        self.write(self.source / 'SKILL.md', '---\nname: explain\n---\nExplain the topic.\n')
        self.write(self.source / 'CORE.md', self.core)
        self.write(self.source / 'references/guide.md', 'Read the source.\n')
        self.write(self.source / 'scripts/explain', '#!/bin/sh\nprintf "Explain fixture\\n"\n')
        (self.source / 'scripts/explain').chmod(0o755)
        self.write(self.source / 'scripts/diagrams/render.mjs', '// Fixture diagram launcher.\n')

    @staticmethod
    def write(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)

    def plan(self, runtime=None, core_only=True, env=None):
        return installer.make_plan(self.repo, self.home, self.env if env is None else env,
                                   runtime=runtime, core_only=core_only)

    def apply(self, runtime=None, core_only=True, env=None):
        plan = self.plan(runtime, core_only, env)
        self.assertEqual(plan.blockers, [])
        return plan, installer.apply_install(plan, self.backups)

    def existing(self, path=None):
        path = path or self.home / '.agents/skills/explain'
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.source, path)
        return path

    def defaults(self, env=None):
        _, paths = installer.locations(self.home, self.home, self.env if env is None else env,
                                       global_only=True)
        return list(dict.fromkeys(path for group in paths.values() for path in group))

    def aliases(self, env=None):
        roots, _ = installer.locations(self.home, self.home, self.env if env is None else env,
                                       global_only=True)
        return list(dict.fromkeys(path / 'explain' for group in roots.values() for path in group))

    def snapshot(self, root=None):
        root = root or self.home
        result = {}
        for path in sorted(root.rglob('*')):
            info = path.lstat()
            content = (os.readlink(path) if path.is_symlink() else None if path.is_dir()
                       else path.read_bytes())
            result[str(path.relative_to(root))] = (info.st_mode, info.st_mtime_ns, content)
        return result

    def assert_blocked_without_writes(self, plan):
        self.assertTrue(plan.blockers)
        before = self.snapshot(self.base)
        with self.assertRaises(ValueError):
            installer.apply_install(plan, self.backups)
        self.assertEqual(self.snapshot(self.base), before)
        self.assertFalse(self.backups.exists())

    def cli(self, *arguments, env=None):
        # Do not inherit harness paths or configuration variables from the user's session.
        isolated = {
            'HOME': str(self.home), 'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
            'SHELL': '/bin/bash', 'PYTHONDONTWRITEBYTECODE': '1',
            'CODEX_HOME': str(self.home / '.codex'),
            'CLAUDE_CONFIG_DIR': str(self.home / '.claude'),
            'XDG_CONFIG_HOME': str(self.home / '.config'),
            'XDG_DATA_HOME': str(self.home / '.local/share'),
            'XDG_STATE_HOME': str(self.home / '.local/state'),
            **(env or {}),
        }
        return subprocess.run([sys.executable, '-B', str(SCRIPT), *arguments],
                              cwd=self.base, env=isolated, capture_output=True,
                              text=True, timeout=30)

    @staticmethod
    def cli_json(stdout):
        # The successful CLI follows its JSON result with terminal restart guidance.
        return json.JSONDecoder().raw_decode(stdout.lstrip())[0]

    def test_fresh_core_install_shares_one_copy_across_all_three_harnesses(self):
        plan, result = self.apply()

        self.assertEqual(result['status'], 'applied')
        self.assertEqual(plan.target, self.home / '.agents/skills/explain')
        expected, errors = installer.inventory(self.source)
        actual, installed_errors = installer.inventory(plan.target)
        self.assertEqual(errors, [])
        self.assertEqual(installed_errors, [])
        self.assertEqual(actual, expected)
        self.assertEqual(stat.S_IMODE((plan.target / 'scripts/explain').stat().st_mode), 0o755)
        for path in self.aliases():
            with self.subTest(alias=path):
                self.assertEqual(path.resolve(strict=True), plan.target)
                self.assertEqual(path.is_symlink(), path != plan.target)
        launcher = self.home / '.local/bin/explain'
        self.assertTrue(launcher.is_symlink())
        self.assertEqual(launcher.resolve(strict=True), plan.target / 'scripts/explain')
        invoked = subprocess.run([str(launcher)], capture_output=True, text=True, timeout=5)
        self.assertEqual(invoked.returncode, 0, invoked.stderr)
        self.assertEqual(invoked.stdout, 'Explain fixture\n')
        for path in self.defaults():
            data = path.read_text()
            self.assertEqual(data.count(START), 1)
            self.assertEqual(data.count(END), 1)
            self.assertIn(self.core.strip(), data)
            self.assertIn(str(plan.target / 'SKILL.md'), data)
        report = installer.build_report(self.source, self.home, home=self.home,
                                        env=self.env, global_only=True)
        self.assertTrue(report['ok'], report['findings'])
        self.assertEqual(set(report['harnesses']), {'codex', 'claude-code', 'opencode'})
        self.assertTrue(all(item['distinct_targets'] == 1 for item in report['harnesses'].values()))
        receipt = self.home / '.local/state/explain/toolchain.json'
        self.assertTrue(json.loads(receipt.read_text())['core_only'])
        self.assertIsNone(json.loads(receipt.read_text())['runtime'])
        self.assertEqual(stat.S_IMODE(receipt.stat().st_mode), 0o600)

    def test_defaults_enroll_unmarked_content_and_preserve_marked_outside_bytes_and_crlf(self):
        marked, unmarked, linked = self.defaults()
        prefix = '# User café instructions\r\n\r\n'.encode()
        suffix = b'\r\n\r\n## Preserve this section\r\nKeep its bytes.\r\n'
        self.write(marked, prefix + START.encode() + b'\r\nOld core.\r\n' + END.encode() + suffix)
        marked.chmod(0o640)
        unmarked_before = b'# Existing defaults\r\nKeep this exact final line.'
        self.write(unmarked, unmarked_before)
        unmarked.chmod(0o600)
        linked_target = self.base / 'private/instructions.md'
        self.write(linked_target, b'# Shared user instructions\n')
        linked.parent.mkdir(parents=True, exist_ok=True)
        linked.symlink_to(linked_target)

        plan, _ = self.apply()

        after = marked.read_bytes()
        self.assertEqual(after.split(START.encode(), 1)[0], prefix)
        self.assertEqual(after.split(END.encode(), 1)[1], suffix)
        block = after.split(START.encode(), 1)[1].split(END.encode(), 1)[0]
        self.assertNotIn(b'\n', block.replace(b'\r\n', b''))
        self.assertIn(self.core.strip().replace('\n', '\r\n').encode(), block)
        self.assertTrue(unmarked.read_bytes().startswith(unmarked_before + b'\r\n\r\n'))
        self.assertNotIn(b'\n', unmarked.read_bytes().replace(b'\r\n', b''))
        self.assertEqual(stat.S_IMODE(marked.stat().st_mode), 0o640)
        self.assertEqual(stat.S_IMODE(unmarked.stat().st_mode), 0o600)
        self.assertTrue(linked.is_symlink())
        self.assertEqual(linked.resolve(strict=True), linked_target)
        self.assertTrue(linked_target.read_bytes().startswith(b'# Shared user instructions\n'))
        self.assertIn(str(plan.target / 'SKILL.md').encode(), linked_target.read_bytes())

    def test_zsh_and_bash_profiles_parse_and_add_the_shortcut_to_path_once(self):
        for shell in ('zsh', 'bash'):
            executable = shutil.which(shell)
            if executable is None:
                continue
            with self.subTest(shell=shell):
                home = self.base / ('home-' + shell)
                home.mkdir()
                profiles = ([home / '.zshrc', home / '.zprofile'] if shell == 'zsh'
                            else [home / '.bashrc', home / '.bash_profile'])
                for profile in profiles:
                    self.write(profile, '# Preserve the existing profile.\n')
                untouched = home / '.profile'
                if shell == 'bash':
                    self.write(untouched, '# A different login profile.\n')
                plan = installer.make_plan(self.repo, home, {'SHELL': executable}, core_only=True)
                self.assertEqual(plan.blockers, [])
                installer.apply_install(plan, self.base / ('backups-' + shell))
                for profile in profiles:
                    parsed = subprocess.run([executable, '-n', str(profile)],
                                            capture_output=True, text=True, timeout=5)
                    self.assertEqual(parsed.returncode, 0, parsed.stderr)
                    tool_dirs = [str(Path(sys.executable).parent)]
                    tool_dirs.extend(str(Path(shutil.which(name)).absolute().parent)
                                     for name in ('node', 'ffmpeg') if shutil.which(name))
                    existing_tools = ':'.join(dict.fromkeys(tool_dirs)) + ':/usr/bin:/bin'
                    for initial_path in ('/usr/bin:/bin', existing_tools,
                                         str(home / '.local/bin') + ':/usr/bin:/bin'):
                        sourced = subprocess.run(
                            [executable, '-c', '. "$1"; . "$1"; printf "%s" "$PATH"',
                             'explain-profile-test', str(profile)],
                            env={'HOME': str(home), 'PATH': initial_path},
                            capture_output=True, text=True, timeout=5)
                        self.assertEqual(sourced.returncode, 0, sourced.stderr)
                        self.assertEqual(sourced.stdout.split(':').count(str(home / '.local/bin')), 1)
                        self.assertEqual(sourced.stdout.split(':')[1:],
                                         [part for part in initial_path.split(':') if part != str(home / '.local/bin')])
                    self.assertTrue(profile.read_bytes().startswith(b'# Preserve the existing profile.\n'))
                if shell == 'bash':
                    self.assertEqual(untouched.read_text(), '# A different login profile.\n')

    def test_backups_are_private_complete_and_repeated_install_makes_no_changes(self):
        default = self.defaults()[0]
        self.write(default, b'# Existing private instructions.\n')
        default.chmod(0o600)
        before = default.read_bytes()

        _, result = self.apply()

        backup = Path(result['backup_directory'])
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((backup / 'manifest.json').stat().st_mode), 0o600)
        manifest = json.loads((backup / 'manifest.json').read_text())
        self.assertEqual(manifest['status'], 'applied')
        regular = Path(manifest['regular_files'])
        self.assertEqual(stat.S_IMODE(regular.stat().st_mode), 0o700)
        records = json.loads((regular / 'manifest.json').read_text())['files']
        saved = next(record for record in records if record['path'] == str(default))
        self.assertEqual((regular / saved['backup_file']).read_bytes(), before)
        for path in backup.rglob('*'):
            if path.is_file():
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600, str(path))
        snapshot = self.snapshot(self.base)
        repeat = self.plan()
        self.assertEqual(repeat.blockers, [])
        self.assertEqual(repeat.files.operations, [])
        self.assertEqual(repeat.links, [])
        self.assertEqual(installer.apply_install(repeat, self.backups),
                         {'status': 'no_changes', 'backup_directory': None})
        self.assertEqual(self.snapshot(self.base), snapshot)

    def test_one_existing_shared_or_legacy_installation_remains_the_shared_target(self):
        for relative in ('.agents/skills/explain', '.codex/skills/explain',
                         '.claude/skills/explain', '.config/opencode/skills/explain'):
            with self.subTest(existing=relative):
                home = self.base / relative.replace('/', '_')
                home.mkdir()
                existing = self.existing(home / relative)
                self.write(existing / 'CORE.md', 'An older installed core.\n')
                self.write(existing / 'node_modules/local-package/index.js', 'Retain local dependencies.\n')
                plan = installer.make_plan(self.repo, home, self.env, core_only=True)
                self.assertEqual(plan.blockers, [])
                self.assertEqual(plan.target, existing)
                installer.apply_install(plan, self.base / (home.name + '-backups'))
                self.assertFalse(existing.is_symlink())
                self.assertEqual((existing / 'CORE.md').read_text(), self.core)
                self.assertEqual((existing / 'node_modules/local-package/index.js').read_text(),
                                 'Retain local dependencies.\n')
                roots, _ = installer.locations(home, home, self.env, global_only=True)
                for root in {path for paths in roots.values() for path in paths}:
                    self.assertEqual((root / 'explain').resolve(strict=True), existing)

    def test_separate_copies_block_all_writes_even_when_content_matches(self):
        self.existing()
        self.existing(self.home / '.codex/skills/explain')
        self.assert_blocked_without_writes(self.plan())

    def test_reinstall_restores_the_launcher_executable_mode(self):
        self.apply()
        executable = self.home / '.agents/skills/explain/scripts/explain'
        executable.chmod(0o644)

        _, result = self.apply()

        self.assertEqual(result['status'], 'applied')
        mode = stat.S_IMODE(executable.stat().st_mode)
        self.assertTrue(mode & stat.S_IXUSR)
        self.assertEqual(mode & ~stat.S_IXUSR, 0o644)
        invoked = subprocess.run([str(self.home / '.local/bin/explain')],
                                 capture_output=True, text=True, timeout=5)
        self.assertEqual(invoked.returncode, 0, invoked.stderr)
        self.assertEqual(invoked.stdout, 'Explain fixture\n')

    def test_alias_parent_retargeted_after_planning_blocks_before_any_writes(self):
        plan = self.plan()
        outside = self.base / 'outside'
        outside.mkdir()
        codex = self.home / '.codex'
        codex.mkdir()
        (codex / 'skills').symlink_to(outside, target_is_directory=True)
        before = self.snapshot(self.base)

        with self.assertRaises((ValueError, RuntimeError)):
            installer.apply_install(plan, self.backups)

        self.assertEqual(self.snapshot(self.base), before)
        self.assertFalse((outside / 'explain').exists())
        self.assertFalse(self.backups.exists())

    def test_conflicting_shortcut_or_skill_path_blocks_all_writes(self):
        for kind in ('shortcut-file', 'shortcut-link', 'skill-file', 'skill-broken-link'):
            with self.subTest(conflict=kind):
                home = self.base / kind
                home.mkdir()
                path = home / ('.local/bin/explain' if kind.startswith('shortcut')
                               else '.claude/skills/explain')
                if kind.endswith('link'):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.symlink_to(self.base / 'unrelated-command')
                else:
                    self.write(path, 'An unrelated user file.\n')
                plan = installer.make_plan(self.repo, home, self.env, core_only=True)
                self.assert_blocked_without_writes(plan)

    def test_incomplete_reversed_or_duplicate_default_markers_block_before_writes(self):
        default = self.defaults()[0]
        for content in (START, END, END + '\n' + START, (START + '\n' + END + '\n') * 2):
            with self.subTest(content=content):
                self.write(default, content)
                self.assert_blocked_without_writes(self.plan())

    def test_invalid_profile_markers_block_before_writes(self):
        self.write(self.home / '.zshrc', '# explain-path:start\nAn incomplete profile block.\n')
        self.assert_blocked_without_writes(self.plan())

    def test_unsupported_shell_blocks_before_writes(self):
        for shell in ('/bin/fish', '/bin/tcsh'):
            with self.subTest(shell=shell):
                self.assert_blocked_without_writes(self.plan(env={'SHELL': shell}))

    def test_backup_directory_inside_source_or_installation_blocks_before_writes(self):
        target = self.existing()
        self.write(target / 'CORE.md', 'An older installed core.\n')
        for backup in (self.source / 'private-backups', target / 'private-backups'):
            with self.subTest(backup=backup):
                plan = self.plan()
                self.assertEqual(plan.blockers, [])
                before = self.snapshot(self.base)
                with self.assertRaises(ValueError):
                    installer.apply_install(plan, backup)
                self.assertEqual(self.snapshot(self.base), before)
                self.assertFalse(backup.exists())

    def test_symlink_failure_restores_regular_files_existing_shortcut_and_created_aliases(self):
        old_skill = self.base / 'old-package'
        self.write(old_skill / 'SKILL.md', 'A prior Explain installation.\n')
        old_command = old_skill / 'scripts/explain'
        self.write(old_command, '#!/bin/sh\nexit 0\n')
        launcher = self.home / '.local/bin/explain'
        launcher.parent.mkdir(parents=True)
        launcher.symlink_to(old_command)
        default = self.defaults()[0]
        self.write(default, '# Existing user instructions.\n')
        default.chmod(0o640)
        plan = self.plan()
        self.assertEqual(plan.blockers, [])
        fail_target = plan.links[-1].target
        self.assertEqual(fail_target, plan.target / 'scripts/explain')
        original_symlink = Path.symlink_to
        injected = False

        def fail_once(path, target, *args, **kwargs):
            nonlocal injected
            if Path(target) == fail_target and not injected:
                injected = True
                raise OSError('Injected shortcut failure')
            return original_symlink(path, target, *args, **kwargs)

        with mock.patch.object(Path, 'symlink_to', new=fail_once):
            with self.assertRaisesRegex(RuntimeError, 'rolled_back.*Injected shortcut failure'):
                installer.apply_install(plan, self.backups)

        self.assertTrue(injected)
        self.assertEqual(default.read_text(), '# Existing user instructions.\n')
        self.assertEqual(stat.S_IMODE(default.stat().st_mode), 0o640)
        self.assertTrue(launcher.is_symlink())
        self.assertEqual(os.readlink(launcher), str(old_command))
        for operation in plan.files.operations:
            if operation.before is None:
                self.assertFalse(operation.path.exists(), str(operation.path))
            else:
                self.assertEqual(operation.path.read_bytes(), operation.before)
        for link in plan.links:
            if link.path != launcher:
                self.assertFalse(link.path.is_symlink(), str(link.path))
        manifest = json.loads(next(self.backups.glob('install-*/manifest.json')).read_text())
        self.assertEqual(manifest['status'], 'rolled_back')
        self.assertEqual(manifest['rollback_errors'], [])

    def test_existing_diagram_modules_move_to_backup_when_runtime_is_enabled(self):
        target = self.existing()
        modules = target / 'scripts/diagrams/node_modules'
        self.write(modules / 'local-package/index.js', b'Original dependency bytes.\x00\xff')
        runtime_root = self.base / 'runtime'
        runtime_modules = runtime_root / 'diagrams/node_modules'
        self.write(runtime_modules / 'pele/package.json', '{"version":"fixture"}\n')
        runtime = {'root': str(runtime_root), 'diagrams': str(runtime_root / 'diagrams'),
                   'python': str(runtime_root / '.venv/bin/python')}

        plan, result = self.apply(runtime=runtime, core_only=False)

        self.assertTrue(modules.is_symlink())
        self.assertEqual(modules.resolve(strict=True), runtime_modules)
        manifest = json.loads((Path(result['backup_directory']) / 'manifest.json').read_text())
        record = next(item for item in manifest['links'] if item['path'] == str(modules))
        saved = Path(result['backup_directory']) / record['moved_backup']
        self.assertEqual((saved / 'local-package/index.js').read_bytes(), b'Original dependency bytes.\x00\xff')
        self.assertFalse(saved.is_symlink())
        receipt = json.loads((self.home / '.local/state/explain/toolchain.json').read_text())
        self.assertEqual({key: receipt['runtime'][key] for key in runtime}, runtime)
        self.assertFalse(receipt['core_only'])
        repeat = self.plan(runtime=runtime, core_only=False)
        self.assertEqual(repeat.blockers, [])
        self.assertEqual(installer.apply_install(repeat, self.backups)['status'], 'no_changes')

    def test_dependency_link_failure_restores_the_existing_module_directory(self):
        target = self.existing()
        modules = target / 'scripts/diagrams/node_modules'
        self.write(modules / 'local-package/index.js', 'Original dependency bytes.\n')
        runtime_root = self.base / 'runtime'
        runtime_modules = runtime_root / 'diagrams/node_modules'
        runtime_modules.mkdir(parents=True)
        runtime = {'root': str(runtime_root), 'diagrams': str(runtime_root / 'diagrams'),
                   'python': str(runtime_root / '.venv/bin/python')}
        plan = self.plan(runtime=runtime, core_only=False)
        self.assertEqual(plan.blockers, [])
        original_symlink = Path.symlink_to

        def reject_dependency(path, destination, *args, **kwargs):
            if Path(destination) == runtime_modules:
                raise OSError('Injected dependency link failure')
            return original_symlink(path, destination, *args, **kwargs)

        with mock.patch.object(Path, 'symlink_to', new=reject_dependency):
            with self.assertRaisesRegex(RuntimeError, 'rolled_back.*Injected dependency link failure'):
                installer.apply_install(plan, self.backups)

        self.assertTrue(modules.is_dir())
        self.assertFalse(modules.is_symlink())
        self.assertEqual((modules / 'local-package/index.js').read_text(), 'Original dependency bytes.\n')
        self.assertEqual((target / 'CORE.md').read_text(), self.core)
        self.assertFalse((self.home / '.local/bin/explain').exists())
        manifest = json.loads(next(self.backups.glob('install-*/manifest.json')).read_text())
        self.assertEqual(manifest['status'], 'rolled_back')
        self.assertEqual(manifest['rollback_errors'], [])

    def test_custom_configuration_and_state_paths_stay_inside_the_isolated_home(self):
        env = {
            'SHELL': '/bin/bash',
            'CODEX_HOME': str(self.home / 'custom/codex'),
            'CLAUDE_CONFIG_DIR': str(self.home / 'custom/claude'),
            'XDG_CONFIG_HOME': str(self.home / 'custom/config'),
            'OPENCODE_CONFIG_DIR': str(self.home / 'custom/opencode'),
            'XDG_DATA_HOME': str(self.home / 'custom/data'),
            'XDG_STATE_HOME': str(self.home / 'custom/state'),
        }
        plan, _ = self.apply(env=env)
        for path in self.aliases(env):
            self.assertEqual(path.resolve(strict=True), plan.target)
        for path in self.defaults(env):
            self.assertIn(str(plan.target / 'SKILL.md'), path.read_text())
        self.assertEqual(len(self.defaults(env)), 4)
        self.assertTrue((self.home / 'custom/state/explain/toolchain.json').is_file())
        for absent in ('.codex', '.claude', '.config', '.local/state', '.local/share'):
            self.assertFalse((self.home / absent).exists(), absent)
        for operation in plan.files.operations:
            self.assertTrue(operation.path.is_relative_to(self.home), str(operation.path))
        for link in plan.links:
            self.assertTrue(link.path.is_relative_to(self.home), str(link.path))

    def test_cli_core_only_installs_the_full_skill_and_repeats_without_changes(self):
        result = self.cli('--core-only')

        self.assertEqual(result.returncode, 0, result.stderr)
        installed = self.cli_json(result.stdout)
        self.assertEqual(installed['status'], 'applied')
        self.assertEqual(installed['doctor_findings'], 0)
        self.assertIsNone(installed['runtime'])
        target = self.home / '.agents/skills/explain'
        expected, errors = installer.inventory(ROOT / 'skills/explain')
        self.assertEqual(errors, [])
        self.assertEqual(installer.inventory(target), (expected, []))
        self.assertTrue((target / 'scripts/explain_doctor.py').is_file())
        self.assertTrue((self.home / '.local/bin/explain').is_symlink())
        snapshot = self.snapshot()
        repeated = self.cli('--core-only')
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(self.cli_json(repeated.stdout)['status'], 'no_changes')
        self.assertEqual(self.snapshot(), snapshot)

    def test_cli_dry_run_reports_full_tool_setup_without_writing_any_files(self):
        before = self.snapshot(self.base)

        result = self.cli('--dry-run')

        self.assertEqual(result.returncode, 0, result.stderr)
        preview = self.cli_json(result.stdout)
        self.assertEqual(preview['status'], 'dry_run')
        self.assertEqual(set(preview['tools']),
                         {'Pele', 'Remotion', 'Kokoro', 'Chrome Headless Shell', 'FFmpeg'})
        self.assertTrue(preview['plan']['files']['actions'])
        self.assertTrue(preview['plan']['links'])
        self.assertEqual(self.snapshot(self.base), before)

    def test_cli_honors_all_custom_configuration_and_state_paths(self):
        env = {
            'CODEX_HOME': str(self.home / 'custom/codex'),
            'CLAUDE_CONFIG_DIR': str(self.home / 'custom/claude'),
            'XDG_CONFIG_HOME': str(self.home / 'custom/config'),
            'OPENCODE_CONFIG_DIR': str(self.home / 'custom/opencode'),
            'XDG_DATA_HOME': str(self.home / 'custom/data'),
            'XDG_STATE_HOME': str(self.home / 'custom/state'),
        }

        result = self.cli('--core-only', env=env)

        self.assertEqual(result.returncode, 0, result.stderr)
        installed = self.cli_json(result.stdout)
        self.assertEqual(installed['doctor_findings'], 0)
        self.assertEqual(Path(installed['backup_directory']).parent,
                         self.home / 'custom/state/explain/backups')
        for path in self.defaults(env):
            self.assertTrue(path.is_file())
        self.assertTrue((self.home / 'custom/state/explain/toolchain.json').is_file())
        for absent in ('.codex', '.claude', '.config', '.local/state', '.local/share'):
            self.assertFalse((self.home / absent).exists(), absent)

    def test_default_main_prepares_tools_before_writing_active_defaults(self):
        runtime_root = self.base / 'runtime'
        (runtime_root / 'diagrams/node_modules').mkdir(parents=True)
        runtime = {'root': str(runtime_root), 'diagrams': str(runtime_root / 'diagrams'),
                   'python': str(runtime_root / '.venv/bin/python')}
        prepared = False

        def prepare(repo, destination, model_cache):
            nonlocal prepared
            self.assertEqual(repo, self.repo)
            self.assertEqual(destination, self.home / '.local/share/explain/runtimes')
            self.assertIsNone(model_cache)
            self.assertEqual(list(self.home.iterdir()), [])
            prepared = True
            return runtime

        module = types.ModuleType('install_runtime')
        module.prepare_runtime = prepare
        with mock.patch.object(installer, 'ROOT', self.repo), \
                mock.patch.object(installer.Path, 'home', return_value=self.home), \
                mock.patch.dict(os.environ, self.env, clear=True), \
                mock.patch.dict(sys.modules, {'install_runtime': module}), \
                mock.patch('builtins.print'):
            status = installer.main([])

        self.assertEqual(status, 0)
        self.assertTrue(prepared)
        receipt = json.loads((self.home / '.local/state/explain/toolchain.json').read_text())
        self.assertEqual({key: receipt['runtime'][key] for key in runtime}, runtime)
        self.assertFalse(receipt['core_only'])
        for path in self.defaults():
            self.assertTrue(path.is_file())

    def test_runtime_preparation_failure_leaves_all_active_files_untouched(self):
        module = types.ModuleType('install_runtime')
        module.prepare_runtime = mock.Mock(side_effect=RuntimeError('Injected runtime failure'))
        before = self.snapshot(self.base)
        with mock.patch.object(installer, 'ROOT', self.repo), \
                mock.patch.object(installer.Path, 'home', return_value=self.home), \
                mock.patch.dict(os.environ, self.env, clear=True), \
                mock.patch.dict(sys.modules, {'install_runtime': module}), \
                mock.patch('builtins.print'):
            status = installer.main([])

        self.assertEqual(status, 2)
        self.assertEqual(self.snapshot(self.base), before)
        module.prepare_runtime.assert_called_once()

    def test_extra_package_files_block_before_preparing_or_downloading_tools(self):
        target = self.existing()
        extra = target / 'local-note.txt'
        self.write(extra, 'Preserve this local addition.\n')
        module = types.ModuleType('install_runtime')
        module.prepare_runtime = mock.Mock(side_effect=AssertionError('Runtime must not start'))
        before = self.snapshot(self.base)
        with mock.patch.object(installer, 'ROOT', self.repo), \
                mock.patch.object(installer.Path, 'home', return_value=self.home), \
                mock.patch.dict(os.environ, self.env, clear=True), \
                mock.patch.dict(sys.modules, {'install_runtime': module}), \
                mock.patch('builtins.print'):
            status = installer.main([])

        self.assertEqual(status, 2)
        self.assertEqual(extra.read_text(), 'Preserve this local addition.\n')
        self.assertEqual(self.snapshot(self.base), before)
        module.prepare_runtime.assert_not_called()


if __name__ == '__main__':
    unittest.main()
