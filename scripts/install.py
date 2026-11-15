"""Install Explain and its local toolchain for all three harnesses."""
import argparse
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import stat
import sys
sys.dont_write_bytecode = True
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/explain/scripts'))
from explain_doctor import build_report, fingerprint, inventory, locations
from explain_loading import routing
from explain_repair import Operation, Plan, apply_plan, atomic_write, replace_block, restore_operation, transactional, transaction_signals


@dataclass
class Link:
    path: Path
    target: Path
    before: tuple
    replace_directory: bool = False
    destination: Path = None

    def __post_init__(self):
        self.destination = self.path.parent.resolve(strict=False) / self.path.name


@dataclass
class Installation:
    files: Plan
    target: Path
    links: list = field(default_factory=list)
    blockers: list = field(default_factory=list)

    def summary(self):
        return {'target': str(self.target), 'files': self.files.summary(),
                'links': [{'path': str(link.path), 'target': str(link.target),
                           'replaces': link.before[0]} for link in self.links],
                'blockers': self.blockers}


def signature(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return ('missing',)
    if stat.S_ISLNK(info.st_mode):
        return ('link', os.readlink(path))
    if stat.S_ISDIR(info.st_mode):
        return ('directory', info.st_dev, info.st_ino, info.st_mtime_ns)
    return ('file', info.st_dev, info.st_ino, info.st_mtime_ns)


def managed_block(before, start, end, content):
    """Enroll or replace one marked span without normalizing surrounding bytes."""
    a, b = start.encode(), end.encode()
    if before.count(a) != before.count(b) or before.count(a) > 1:
        raise ValueError('Invalid managed block markers')
    newline = b'\r\n' if b'\r\n' in before else b'\n'
    block = a + newline + content.strip().replace('\r\n', '\n').replace('\n', newline.decode()).encode() + newline + b
    if a in before:
        first, last = before.index(a), before.index(b)
        if last < first:
            raise ValueError('Managed block markers are reversed')
        return before[:first] + block + before[last + len(b):]
    return before + (newline if before and not before.endswith(b'\n') else b'') + (newline if before else b'') + block + newline


def make_plan(repo, home, env, runtime=None, core_only=False):
    home = home.resolve()
    source = (repo / 'skills/explain').resolve(strict=True)
    expected, errors = inventory(source)
    if errors:
        raise ValueError('Cannot read the complete skill reference')
    report = build_report(source, home, home=home, env=env, global_only=True)
    targets = {Path(item['resolved']) for item in report['installations'].values() if item.get('kind') == 'directory'}
    target = next(iter(targets)) if len(targets) == 1 else home / '.agents/skills/explain'
    files = Plan(source, fingerprint(expected))
    result = Installation(files, target)
    if len(targets) > 1:
        result.blockers.append('Separate Explain installations exist. Resolve them before installation.')
    for finding in report['findings']:
        if finding['code'] not in ('installation_not_found', 'installation_different', 'defaults_different',
                                   'route_content_different', 'route_missing', 'route_relative_unresolved', 'defaults_override_unmanaged'):
            result.blockers.append('Resolve ' + finding['code'] + ': ' + finding.get('path', finding.get('harness', '')))
    if target.exists():
        current, errors = inventory(target)
        if errors:
            result.blockers.append('The existing installation is unreadable')
        files.installations[target] = fingerprint(current)
        extras = sorted(current.keys() - expected.keys())
        if extras:
            result.blockers.append('Extra package files require manual resolution: ' + ', '.join(extras))
    operations = {}

    def add_file(path, data, kind, new_mode=0o644, package=False):
        try:
            resolved = path.resolve(strict=False)
            if package and not resolved.is_relative_to(target):
                raise ValueError('Package symlink escapes the installation')
            if resolved.is_relative_to(source):
                raise ValueError('Installation would change the source package')
            if path.is_symlink() and not path.exists():
                raise ValueError('Broken file link requires manual resolution')
            for parent in resolved.parents:
                if parent.exists() and not parent.is_dir():
                    raise ValueError('Destination parent is not a directory')
            if resolved.exists() and not resolved.is_file():
                raise ValueError('Destination is not a regular file')
            before = resolved.read_bytes() if resolved.exists() else None
            mode = stat.S_IMODE(resolved.stat().st_mode) if before is not None else new_mode
            after_mode = mode | (new_mode & 0o100) if package else mode
            if before == data and after_mode == mode:
                return
            op = Operation(resolved, path, kind, before, data, mode, after_mode)
            if resolved in operations and operations[resolved].after != data:
                raise ValueError('Conflicting writes target the same file')
            operations[resolved] = op
        except (OSError, RuntimeError, ValueError) as exc:
            result.blockers.append(f'{path}: {exc}')

    for relative in expected:
        path = source / relative
        add_file(target / relative, path.read_bytes(), 'skill', stat.S_IMODE(path.stat().st_mode), package=True)
    roots, defaults = locations(home, home, env, global_only=True)
    # Native and compatible global roots all point to the same copy.
    for root in dict.fromkeys(path for paths in roots.values() for path in paths):
        path = root / 'explain'
        if path == target:
            continue
        try:
            if path.resolve(strict=False) == target:
                files.aliases[path] = target
                continue
        except (OSError, RuntimeError):
            pass
        old = signature(path)
        if old[0] != 'missing':
            result.blockers.append('Conflicting skill path: ' + str(path))
        else:
            result.links.append(Link(path, target, old))
    core = (source / 'CORE.md').read_text()
    for path in dict.fromkeys(path for paths in defaults.values() for path in paths):
        try:
            before = path.read_bytes() if path.exists() else b''
            content = core.strip() + '\n\n' + routing(target).strip()
            after = managed_block(before, '<!-- explain-writing-default:start -->',
                                  '<!-- explain-writing-default:end -->', content)
            add_file(path, after, 'defaults')
        except (OSError, ValueError) as exc:
            result.blockers.append(f'{path}: {exc}')
    shell = Path(env.get('SHELL', '/bin/zsh' if sys.platform == 'darwin' else '/bin/bash')).name
    if shell not in ('bash', 'zsh', 'sh'):
        result.blockers.append('Automatic PATH setup supports Bash and Zsh. Unsupported shell: ' + shell)
    if shell == 'zsh':
        profile_root = Path(env.get('ZDOTDIR') or home).expanduser().resolve(strict=False)
        profiles = [profile_root / '.zshrc', profile_root / '.zprofile']
    else:
        login = next((home / name for name in ('.bash_profile', '.bash_login', '.profile') if (home / name).exists()), home / '.profile')
        profiles = [home / '.bashrc', login]
    path_content = ('# Explain terminal command\ncase ":$PATH:" in\n'
                    '  *":$HOME/.local/bin:"*) ;;\n'
                    '  *) export PATH="$HOME/.local/bin:$PATH" ;;\nesac')
    for path in profiles:
        try:
            before = path.read_bytes() if path.exists() else b''
            # Shell comments, not HTML comments, make the profile valid shell code.
            after = managed_block(before, '# explain-path:start', '# explain-path:end', path_content)
            add_file(path, after, 'shell_profile')
        except (OSError, ValueError) as exc:
            result.blockers.append(f'{path}: {exc}')
    launcher = home / '.local/bin/explain'
    wanted = target / 'scripts/explain'
    old = signature(launcher)
    if old[0] == 'link':
        try:
            correct = launcher.resolve(strict=False) == wanted
            previous = launcher.resolve(strict=False)
            owned = previous.name == 'explain' and ((previous.parent.parent / 'SKILL.md').is_file() or (previous.parent.parent / 'skills/explain/SKILL.md').is_file())
        except (OSError, RuntimeError):
            correct, owned = False, False
        if not correct:
            if owned:
                result.links.append(Link(launcher, wanted, old))
            else:
                result.blockers.append('Another shortcut owns this command: ' + str(launcher))
    elif old[0] == 'missing':
        result.links.append(Link(launcher, wanted, old))
    else:
        result.blockers.append('Another file owns this command: ' + str(launcher))
    if runtime:
        modules = target / 'scripts/diagrams/node_modules'
        wanted = Path(runtime['diagrams']) / 'node_modules'
        old = signature(modules)
        if modules.resolve(strict=False) != wanted:
            if old[0] in ('missing', 'link', 'directory'):
                result.links.append(Link(modules, wanted, old, old[0] == 'directory'))
            else:
                result.blockers.append('Invalid diagram dependency path: ' + str(modules))
    state = Path(env.get('XDG_STATE_HOME') or home / '.local/state')
    stable_runtime = {key: runtime[key] for key in ('id', 'root', 'video', 'diagrams', 'venv', 'python',
                      'models', 'browser', 'marker', 'versions', 'hashes') if key in runtime} if runtime else None
    if (state / 'explain/toolchain.json').resolve(strict=False).is_relative_to(target):
        result.blockers.append('The state directory must stay outside the managed skill')
    if stable_runtime:
        stable_runtime['executables'] = {name: shutil.which(name) for name in ('node', 'npm', 'ffmpeg', 'ffprobe')}
    if core_only and not stable_runtime:
        previous_receipt = state / 'explain/toolchain.json'
        if previous_receipt.exists():
            try:
                previous_runtime = json.loads(previous_receipt.read_text()).get('runtime')
                if isinstance(previous_runtime, dict):
                    stable_runtime = previous_runtime
            except (OSError, ValueError, AttributeError):
                result.blockers.append('Cannot preserve the existing toolchain receipt')
    receipt = {'schema_version': 1, 'skill': str(target), 'reference_fingerprint': fingerprint(expected),
               'core_only': not bool(stable_runtime), 'runtime': stable_runtime}
    add_file(state / 'explain/launcher-python', (getattr(sys, '_base_executable', sys.executable) + '\n').encode(), 'launcher_interpreter', 0o600)
    add_file(state / 'explain/toolchain.json', (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode(), 'toolchain', 0o600)
    for op in operations.values():
        if op.kind != 'skill' and (op.path.is_relative_to(target) or op.path.is_relative_to(source)):
            result.blockers.append('Configuration overlaps the managed skill or source: ' + str(op.input_path))
    for link in result.links:
        if link.path != target / 'scripts/diagrams/node_modules' and (link.destination.is_relative_to(target) or link.destination.is_relative_to(source)):
            result.blockers.append('Alias overlaps the managed skill or source: ' + str(link.path))
    files.operations = sorted(operations.values(), key=lambda op: str(op.path))
    result.blockers = list(dict.fromkeys(result.blockers))
    return result


@transactional
def apply_install(plan, backup_base):
    if plan.blockers:
        raise ValueError('; '.join(plan.blockers))
    for link in plan.links:
        if (link.path.parent.resolve(strict=False) / link.path.name != link.destination
                or signature(link.path) != link.before):
            raise ValueError('Shortcut changed before installation: ' + str(link.path))
    if not plan.files.operations and not plan.links:
        return {'status': 'no_changes', 'backup_directory': None}
    backup_base = backup_base.resolve(strict=False)
    if any(backup_base.is_relative_to(root) for root in (plan.target, plan.files.reference)):
        raise ValueError('Backups must stay outside the source and managed installation')
    backup_base.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = Path(tempfile.mkdtemp(prefix='install-', dir=backup_base))
    (backup / 'moved').mkdir(mode=0o700)
    manifest = {'status': 'prepared', 'links': [], 'regular_files': None}
    for i, link in enumerate(plan.links):
        manifest['links'].append({'path': str(link.path), 'target': str(link.target),
                                  'before': list(link.before), 'moved_backup': 'moved/' + str(i) if link.replace_directory else None})
    manifest_path = backup / 'manifest.json'
    def save():
        atomic_write(manifest_path, (json.dumps(manifest, indent=2) + '\n').encode(), 0o600)
    save()
    completed = []
    regular_applied = False
    try:
        def acknowledge(regular):
            nonlocal regular_applied
            regular_applied = True
            manifest['regular_files'] = regular['backup_directory']
        regular = apply_plan(plan.files, backup / 'regular-files', on_applied=acknowledge)
        save()
        for i, link in enumerate(plan.links):
            if (link.path.parent.resolve(strict=False) / link.path.name != link.destination
                    or signature(link.path) != link.before):
                raise ValueError('Shortcut changed during installation: ' + str(link.path))
            link.destination.parent.mkdir(parents=True, exist_ok=True)
            moved = backup / 'moved' / str(i)
            if link.replace_directory:
                completed.append((link, moved))
                os.rename(link.destination, moved)
            else:
                completed.append((link, None))
            temporary = link.destination.parent / ('.explain-' + backup.name + '-' + str(i))
            try:
                temporary.symlink_to(link.target)
                os.replace(temporary, link.destination)
            finally:
                if temporary.is_symlink():
                    temporary.unlink()
        manifest['status'] = 'applied'
        save()
        return {'status': 'applied', 'backup_directory': str(backup)}
    except BaseException as exc:
        errors = list(getattr(exc, 'rollback_errors', []))
        if getattr(exc, 'backup_directory', None) and not regular_applied:
            manifest['regular_files'] = exc.backup_directory
        with transaction_signals(rollback=True):
            for link, moved in reversed(completed):
                try:
                    restore_link(link, moved)
                except BaseException as error:
                    errors.append(str(error))
            if regular_applied:
                for op in reversed(plan.files.operations):
                    try:
                        restore_operation(op)
                    except BaseException as error:
                        errors.append(str(error))
            manifest.update(status='rollback_failed' if errors else 'rolled_back',
                            error=str(exc) or type(exc).__name__, rollback_errors=errors)
            save()
        message = f'Installation failed. Backup: {backup}. State: {manifest["status"]}. {exc}'
        failure = KeyboardInterrupt(message) if isinstance(exc, KeyboardInterrupt) else RuntimeError(message)
        failure.backup_directory = str(backup)
        failure.rollback_errors = errors
        raise failure from exc


def restore_link(link, moved):
    if link.destination.parent.resolve(strict=False) / link.destination.name != link.destination:
        raise RuntimeError('Rollback conflict: alias parent changed: ' + str(link.path))
    current = signature(link.destination)
    if current == link.before and (moved is None or not moved.exists()):
        return
    owned = current == ('link', str(link.target))
    if moved is not None and moved.exists():
        if not owned and current[0] != 'missing':
            raise RuntimeError('Rollback conflict: alias edits preserved: ' + str(link.path))
        if owned:
            link.destination.unlink()
        os.rename(moved, link.destination)
    elif owned:
        link.destination.unlink()
        if link.before[0] == 'link':
            link.destination.symlink_to(link.before[1])
    else:
        raise RuntimeError('Rollback conflict: alias edits preserved: ' + str(link.path))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--core-only', action='store_true', help='Install the skill and defaults without media dependencies')
    parser.add_argument('--model-cache', type=Path, help='Reuse verified Kokoro model files from this directory')
    args = parser.parse_args(argv)
    home = Path.home().resolve()
    env = dict(os.environ)
    data = Path(env.get('XDG_DATA_HOME') or home / '.local/share')
    state = Path(env.get('XDG_STATE_HOME') or home / '.local/state')
    activation = None
    try:
        preview = make_plan(ROOT, home, env, core_only=args.core_only)
        if preview.blockers:
            raise ValueError('; '.join(preview.blockers))
        if args.dry_run:
            print(json.dumps({'status': 'dry_run', 'plan': preview.summary(),
                              'tools': [] if args.core_only else ['Pele', 'Remotion', 'Kokoro', 'Chrome Headless Shell', 'FFmpeg']}, indent=2))
            return 0
        runtime = None
        if any(data.resolve(strict=False).is_relative_to(root) for root in (preview.target, preview.files.reference)):
            raise ValueError('The data directory must stay outside the source and managed skill')
        if not args.core_only:
            from install_runtime import prepare_runtime
            runtime = prepare_runtime(ROOT, data / 'explain/runtimes', args.model_cache)
        if fingerprint(inventory(preview.files.reference)[0]) != preview.files.reference_hash:
            raise ValueError('The source changed while preparing tools. Run installation again.')
        plan = make_plan(ROOT, home, env, runtime, args.core_only)
        result = apply_install(plan, state / 'explain/backups')
        activation = result
        report = build_report(plan.files.reference, home, home=home, env=env, global_only=True)
        if not report['ok']:
            raise ValueError('Installation activated but verification found issues. Backup: ' + str(result['backup_directory']) + '. Findings: ' + json.dumps(report['findings']))
        result.update(skill=str(plan.target), launcher=str(home / '.local/bin/explain'),
                      runtime=runtime and runtime['root'], doctor_findings=0)
        print(json.dumps(result, indent=2))
        print('Open a new terminal and start fresh harness sessions to load the updated paths and instructions.')
        return 0
    except (OSError, ValueError, RuntimeError, KeyboardInterrupt) as exc:
        print('Explain install: ' + str(exc), file=sys.stderr)
        if activation is not None:
            print('Configuration status: ' + activation['status'] + '; backup: ' +
                  str(activation['backup_directory']) + '. Post-install verification did not complete.', file=sys.stderr)
        return 130 if isinstance(exc, KeyboardInterrupt) else 2


if __name__ == '__main__':
    sys.exit(main())
