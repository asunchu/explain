"""Exercise installed tools without a checkout on the subprocess import path."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


SKILL = Path(__file__).resolve().parents[1] / 'skills/explain'
START = '<!-- explain-writing-default:start -->'
END = '<!-- explain-writing-default:end -->'


def copy_skill(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    return Path(shutil.copytree(
        source, destination,
        ignore=shutil.ignore_patterns('.git', 'node_modules', '.venv', 'models',
                                      '__pycache__', '.DS_Store', '*.pyc', '.cache'),
    ))


class BundledToolsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.home = self.base / 'home'
        self.project = self.base / 'unrelated-project'
        self.home.mkdir()
        self.project.mkdir()
        (self.project / '.git').mkdir()
        self.bundle = copy_skill(SKILL, self.base / 'copied-skill/explain')
        self.launcher = self.bundle / 'scripts/explain'
        self.bin_dir = self.home / '.local/bin'
        # Deliberately omit the checkout, inherited configuration, and PYTHONPATH.
        self.env = {
            'HOME': str(self.home),
            'PATH': os.pathsep.join((str(self.bin_dir), str(Path(sys.executable).parent), os.defpath)),
            'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONNOUSERSITE': '1',
            'LC_ALL': 'C',
        }

    def run_command(self, arguments):
        return subprocess.run(arguments, cwd=self.project, env=self.env,
                              capture_output=True, text=True, timeout=20)

    def setup_shortcut(self, *arguments):
        return self.run_command([sys.executable, '-B',
                                 str(self.bundle / 'scripts/install-shortcuts.py'), *arguments])

    def doctor(self, *arguments):
        return self.run_command([sys.executable, '-B',
                                 str(self.bundle / 'scripts/explain_doctor.py'),
                                 '--harness', 'codex', '--json', *arguments])

    def installed_copy(self):
        return copy_skill(self.bundle, self.home / '.agents/skills/explain')

    def report(self, result, expected_code=0):
        self.assertEqual(result.returncode, expected_code,
                         'stdout:\n' + result.stdout + '\nstderr:\n' + result.stderr)
        return json.loads(result.stdout)

    def snapshot(self):
        result = {}
        for path in [self.base, *sorted(self.base.rglob('*'))]:
            metadata = path.lstat()
            if path.is_symlink():
                kind, content = 'symlink', os.readlink(path)
            elif path.is_dir():
                kind, content = 'directory', None
            else:
                kind, content = 'file', path.read_bytes()
            result[str(path.relative_to(self.base))] = (
                kind, stat.S_IMODE(metadata.st_mode), metadata.st_mtime_ns, content)
        return result

    def test_shortcut_dry_run_creates_nothing_and_does_not_change_launcher_mode(self):
        self.launcher.chmod(0o644)
        before = self.snapshot()

        result = self.setup_shortcut('--dry-run')

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.bin_dir / 'explain'), result.stdout)
        self.assertIn(str(self.launcher), result.stdout)
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.bin_dir.exists())

    def test_shortcut_launches_copied_skill_from_path_in_another_directory(self):
        self.installed_copy()
        self.launcher.chmod(0o644)

        setup = self.setup_shortcut()
        self.assertEqual(setup.returncode, 0, setup.stderr)
        shortcut = self.bin_dir / 'explain'
        self.assertTrue(shortcut.is_symlink())
        self.assertEqual(shortcut.resolve(), self.launcher)
        self.assertTrue(os.access(shortcut, os.X_OK))

        report = self.report(self.run_command(
            ['explain', 'doctor', '--harness', 'codex', '--json']))

        self.assertEqual(report['reference']['path'], str(self.bundle))
        self.assertEqual(report['project'], str(self.project))
        self.assertTrue(report['ok'])

    def test_repeated_shortcut_setup_preserves_the_existing_shortcut(self):
        first = self.setup_shortcut()
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.snapshot()

        repeated = self.setup_shortcut()

        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(before, self.snapshot())

    def test_shortcut_setup_accepts_an_existing_relative_alias(self):
        self.bin_dir.mkdir(parents=True)
        shortcut = self.bin_dir / 'explain'
        relative_target = os.path.relpath(self.launcher, self.bin_dir)
        shortcut.symlink_to(relative_target)
        before = self.snapshot()

        result = self.setup_shortcut()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(os.readlink(shortcut), relative_target)
        self.assertEqual(before, self.snapshot())
        help_result = self.run_command(['explain', '--help'])
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn('explain doctor', help_result.stdout)

    def test_shortcut_setup_never_replaces_a_regular_file_or_directory(self):
        for kind in ('file', 'directory'):
            with self.subTest(kind=kind):
                directory = self.base / ('conflicting-' + kind)
                directory.mkdir()
                shortcut = directory / 'explain'
                if kind == 'file':
                    shortcut.write_bytes(b'A user command.\x00\xff')
                else:
                    shortcut.mkdir()
                    (shortcut / 'user-file').write_text('Preserve this directory.\n')
                before = self.snapshot()

                for replacement in ((), ('--replace',)):
                    result = self.setup_shortcut('--bin-dir', str(directory), *replacement)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(before, self.snapshot())

    def test_different_symlink_requires_explicit_replacement(self):
        old_target = self.base / 'another-command'
        old_target.write_text('Keep the former target.\n')
        self.bin_dir.mkdir(parents=True)
        shortcut = self.bin_dir / 'explain'
        shortcut.symlink_to(old_target)
        before = self.snapshot()

        refused = self.setup_shortcut()
        self.assertEqual(refused.returncode, 2, refused.stderr)
        self.assertEqual(before, self.snapshot())
        preview = self.setup_shortcut('--replace', '--dry-run')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(before, self.snapshot())

        replaced = self.setup_shortcut('--replace')

        self.assertEqual(replaced.returncode, 0, replaced.stderr)
        self.assertEqual(shortcut.resolve(), self.launcher)
        self.assertEqual(old_target.read_text(), 'Keep the former target.\n')
        self.assertEqual(list(self.bin_dir.iterdir()), [shortcut])

    def test_cyclic_shortcut_requires_replacement_and_dry_run_preserves_the_loop(self):
        self.bin_dir.mkdir(parents=True)
        shortcut = self.bin_dir / 'explain'
        shortcut.symlink_to('explain')
        before = self.snapshot()

        refused = self.setup_shortcut()
        self.assertEqual(refused.returncode, 2, refused.stderr)
        self.assertIn('--replace', refused.stderr)
        self.assertEqual(before, self.snapshot())

        preview = self.setup_shortcut('--replace', '--dry-run')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(os.readlink(shortcut), 'explain')
        self.assertEqual(before, self.snapshot())

        replaced = self.setup_shortcut('--replace')
        self.assertEqual(replaced.returncode, 0, replaced.stderr)
        self.assertEqual(shortcut.resolve(), self.launcher)
        self.assertEqual(list(self.bin_dir.iterdir()), [shortcut])
        help_result = self.run_command(['explain', '--help'])
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn('explain doctor', help_result.stdout)

    def test_direct_doctor_uses_its_own_copied_skill_as_the_default_reference(self):
        core = self.bundle / 'CORE.md'
        core.write_text(core.read_text() + '\nA rule unique to this installed copy.\n')
        installed = self.installed_copy()

        report = self.report(self.doctor())

        self.assertEqual(report['reference']['path'], str(self.bundle))
        self.assertEqual(report['installations'][str(installed)]['state'], 'match')
        self.assertTrue(report['ok'])
        self.assertNotEqual(core.read_bytes(), (SKILL / 'CORE.md').read_bytes())

    def test_copied_doctor_repairs_another_installation_and_marked_defaults(self):
        installed = self.installed_copy()
        core = installed / 'CORE.md'
        old_core = b'# Older writing rules\n\nKeep an old rule.\n'
        core.write_bytes(old_core)
        missing = installed / 'scripts/explain_loading.py'
        missing.unlink()
        defaults = self.home / '.codex/AGENTS.md'
        defaults.parent.mkdir()
        prefix = b'Preserve this personal instruction.\r\n\r\n'
        suffix = b'\r\n\r\nPreserve the trailing instruction.\r\n'
        old_block = (START + '\r\nAn older writing rule.\r\n\r\n'
                     '## Explanation artifacts\r\nRead `'
                     + str(self.base / 'missing-skill/SKILL.md') + '`.\r\n' + END).encode()
        old_defaults = prefix + old_block + suffix
        defaults.write_bytes(old_defaults)

        report = self.report(self.doctor('--reference', str(self.bundle), '--fix'))

        self.assertTrue(report['ok'])
        self.assertEqual(report['reference']['path'], str(self.bundle))
        self.assertEqual(report['repair']['status'], 'applied')
        self.assertEqual(report['repair']['changed_files'], 3)
        self.assertEqual(core.read_bytes(), (self.bundle / 'CORE.md').read_bytes())
        self.assertEqual(missing.read_bytes(), (self.bundle / 'scripts/explain_loading.py').read_bytes())
        updated = defaults.read_bytes()
        self.assertTrue(updated.startswith(prefix + START.encode() + b'\r\n'))
        self.assertTrue(updated.endswith(END.encode() + suffix))
        self.assertIn((self.bundle / 'CORE.md').read_text().strip().replace('\n', '\r\n').encode(), updated)
        default_report = next(item for item in report['harnesses']['codex']['defaults']
                              if item['path'] == str(defaults))
        self.assertEqual(default_report['state'], 'match')
        self.assertEqual(default_report['route_content'], 'match')
        self.assertEqual(default_report['routes'][0]['path'], str(installed / 'SKILL.md'))

        backup = Path(report['repair']['backup_directory'])
        self.assertEqual(backup.parent, self.home / '.local/state/explain/backups')
        manifest = json.loads((backup / 'manifest.json').read_text())
        self.assertEqual(manifest['status'], 'applied')
        saved = {item['path']: item for item in manifest['files']}
        self.assertEqual((backup / saved[str(core)]['backup_file']).read_bytes(), old_core)
        self.assertEqual((backup / saved[str(defaults)]['backup_file']).read_bytes(), old_defaults)
        self.assertIsNone(saved[str(missing)]['backup_file'])

        before = self.snapshot()
        repeated = self.report(self.doctor('--reference', str(self.bundle), '--fix'))
        self.assertEqual(repeated['repair']['status'], 'no_changes')
        self.assertIsNone(repeated['repair']['backup_directory'])
        self.assertEqual(before, self.snapshot())


if __name__ == '__main__':
    unittest.main()
