"""Plan and apply bounded Explain repairs with private backups and rollback."""
from dataclasses import dataclass, field
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import signal
import threading

from explain_doctor import END, START, file_hash, fingerprint, inventory
from explain_loading import routing


@dataclass
class Operation:
    path: Path
    input_path: Path
    kind: str
    before: bytes
    after: bytes
    mode: int
    after_mode: int = None


@dataclass
class Plan:
    reference: Path
    reference_hash: str
    operations: list = field(default_factory=list)
    blockers: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    installations: dict = field(default_factory=dict)
    aliases: dict = field(default_factory=dict)

    def summary(self):
        return {'reference': str(self.reference), 'reference_fingerprint': self.reference_hash,
                'blockers': self.blockers, 'notes': self.notes,
                'actions': [{'path': str(op.path), 'input_path': str(op.input_path), 'kind': op.kind,
                             'action': 'create' if op.before is None else 'update',
                             'before_sha256': checksum(op.before), 'after_sha256': checksum(op.after),
                             'after_mode': op.after_mode if op.after_mode is not None else op.mode}
                            for op in self.operations]}


def checksum(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def replace_block(before, core, installation):
    """Replace only the marked span; preserve every byte outside it."""
    start, end = START.encode(), END.encode()
    if before.count(start) != 1 or before.count(end) != 1 or before.index(end) < before.index(start):
        raise ValueError('Expected one complete writing-default block')
    a, b = before.index(start), before.index(end)
    newline = '\r\n' if b'\r\n' in before[a:b] else '\n'
    content = core.strip() + '\n\n' + routing(installation).strip()
    block = start + newline.encode() + content.replace('\n', newline).encode() + newline.encode() + end
    return before[:a] + block + before[b + len(end):]


def build_plan(report):
    source = Path(report['reference']['path']).resolve(strict=True)
    plan = Plan(source, report['reference']['fingerprint'])
    files, errors = inventory(source)
    if errors or fingerprint(files) != plan.reference_hash:
        plan.blockers.append('The reference changed or became unreadable. Run the doctor again.')
        return plan
    core = (source / 'CORE.md').read_text()
    operations = {}

    def add(path, kind, after, root=None, new_mode=0o644):
        try:
            resolved = path.resolve(strict=False)
            if root and not resolved.is_relative_to(root):
                raise ValueError('Package symlink escapes its installation')
            if path.is_symlink() and not path.exists():
                raise ValueError('Cannot repair a broken file symlink automatically')
            for parent in resolved.parents:
                if parent.exists() and not parent.is_dir():
                    raise ValueError('Destination parent is not a directory')
            if resolved.exists() and not stat.S_ISREG(resolved.stat().st_mode):
                raise ValueError('Destination is not a regular file')
            if resolved.is_relative_to(source):
                raise ValueError('Repair would change the reference package')
            before = resolved.read_bytes() if resolved.exists() else None
            mode = stat.S_IMODE(resolved.stat().st_mode) if before is not None else new_mode
            if before == after:
                return
            op = Operation(resolved, path, kind, before, after, mode)
            if resolved in operations and operations[resolved].after != after:
                raise ValueError('Conflicting repairs target the same file')
            operations[resolved] = op
        except (OSError, RuntimeError, ValueError) as exc:
            plan.blockers.append(f'{path}: {exc}')

    for finding in report['findings']:
        if finding['code'] not in ('installation_different', 'defaults_different',
                                   'route_content_different', 'route_missing', 'route_relative_unresolved'):
            plan.blockers.append('Resolve ' + finding['code'] + ': ' + finding.get('path', finding.get('harness', '')))
    for harness, data in report['harnesses'].items():
        targets = {Path(report['installations'][key]['resolved']) for key in data['candidates']
                   if report['installations'][key].get('kind') == 'directory'}
        if len(targets) != 1:
            plan.blockers.append(f'{harness}: repair requires one unambiguous installation')
            continue
        target = next(iter(targets))
        for key in data['candidates']:
            item = report['installations'][key]
            if item.get('kind') == 'directory':
                plan.aliases[Path(key)] = Path(item['resolved'])
        if target not in plan.installations:
            item = next(report['installations'][key] for key in data['candidates']
                        if report['installations'][key]['resolved'] == str(target))
            plan.installations[target] = item.get('fingerprint')
            if item.get('extra'):
                plan.notes.append(f'{target}: extra files remain unchanged and may leave doctor findings')
            for relative in sorted(set(item.get('changed', []) + item.get('missing', []))):
                add(target / relative, 'skill', (source / relative).read_bytes(), root=target,
                    new_mode=stat.S_IMODE((source / relative).stat().st_mode))
        for default in data['defaults']:
            if default['state'] in ('missing', 'unmanaged'):
                if default['state'] == 'unmanaged':
                    plan.notes.append(default['path'] + ': unmarked instructions remain unchanged')
                continue
            if default['state'] not in ('match', 'different'):
                continue
            path = Path(default['path'])
            try:
                before = path.read_bytes()
                after = replace_block(before, core, target)
                add(path, 'defaults', after)
            except (OSError, RuntimeError, ValueError) as exc:
                plan.blockers.append(f'{path}: {exc}')
    plan.operations = sorted(operations.values(), key=lambda op: str(op.path))
    plan.blockers = list(dict.fromkeys(plan.blockers))
    plan.notes = list(dict.fromkeys(plan.notes))
    return plan


def check_plan(plan):
    if plan.blockers:
        raise ValueError('Repair is blocked: ' + '; '.join(plan.blockers))
    files, errors = inventory(plan.reference)
    if errors or fingerprint(files) != plan.reference_hash:
        raise ValueError('Reference changed after planning')
    for alias, target in plan.aliases.items():
        if alias.resolve(strict=True) != target:
            raise ValueError('Installation alias changed after planning: ' + str(alias))
    for target, original in plan.installations.items():
        files, errors = inventory(target)
        if errors or fingerprint(files) != original:
            raise ValueError('Installation changed after planning: ' + str(target))
    for op in plan.operations:
        check_operation(op)


def check_operation(op):
    if op.input_path.resolve(strict=False) != op.path:
        raise ValueError('Destination path changed after planning: ' + str(op.input_path))
    if op.path.exists() and not stat.S_ISREG(op.path.stat().st_mode):
        raise ValueError('Destination type changed after planning: ' + str(op.path))
    current = op.path.read_bytes() if op.path.exists() else None
    if current != op.before or (current is not None and stat.S_IMODE(op.path.stat().st_mode) != op.mode):
        raise ValueError('Destination changed after planning: ' + str(op.path))


def atomic_write(path, data, mode):
    """Replace a regular file on its own filesystem without replacing its symlink alias."""
    fd, name = tempfile.mkstemp(prefix='.explain-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)



@contextmanager
def transaction_signals(rollback=False):
    previous = {}
    if threading.current_thread() is threading.main_thread():
        def cancel(signum, frame):
            raise KeyboardInterrupt('Transaction interrupted')
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, signal.SIG_IGN if rollback else cancel)
    try:
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def transactional(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        with transaction_signals():
            return function(*args, **kwargs)
    return guarded


def restore_operation(op):
    """Restore only our after-state; preserve concurrent edits for manual recovery."""
    if op.path.resolve(strict=False) != op.path:
        raise RuntimeError('Rollback conflict: destination path changed: ' + str(op.path))
    try:
        info = op.path.lstat()
    except FileNotFoundError:
        if op.before is None:
            return
        raise RuntimeError('Rollback conflict: destination was removed: ' + str(op.path))
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError('Rollback conflict: destination type changed: ' + str(op.path))
    current, mode = op.path.read_bytes(), stat.S_IMODE(info.st_mode)
    if op.before is not None and current == op.before and mode == op.mode:
        return
    expected_mode = op.after_mode if op.after_mode is not None else op.mode
    if current != op.after or mode != expected_mode:
        raise RuntimeError('Rollback conflict: concurrent edits preserved: ' + str(op.path))
    if op.before is None:
        op.path.unlink()
    else:
        atomic_write(op.path, op.before, op.mode)


@transactional
def apply_plan(plan, backup_base, on_applied=None):
    check_plan(plan)
    if not plan.operations:
        result = {'status': 'no_changes', 'backup_directory': None, 'changed_files': 0}
        if on_applied:
            on_applied(result)
        return result
    base = backup_base.expanduser().resolve(strict=False)
    if any(base.is_relative_to(root) for root in (plan.reference, *plan.installations)):
        raise ValueError('Backups must stay outside the reference and installation folders')
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-')
    backup = Path(tempfile.mkdtemp(prefix=stamp, dir=base))
    (backup / 'files').mkdir(mode=0o700)
    manifest = {'schema_version': 1, 'status': 'preparing', 'plan': plan.summary(), 'files': []}
    manifest_path = backup / 'manifest.json'
    changed, created_dirs = [], []
    try:
        # Finish and verify every backup before touching any destination.
        for i, op in enumerate(plan.operations):
            record = {'path': str(op.path), 'mode': op.mode, 'before_sha256': checksum(op.before),
                      'after_sha256': checksum(op.after), 'after_mode': op.after_mode if op.after_mode is not None else op.mode, 'backup_file': None}
            if op.before is not None:
                copy = backup / 'files' / str(i)
                atomic_write(copy, op.before, 0o600)
                if file_hash(copy) != checksum(op.before):
                    raise OSError('Backup verification failed')
                record['backup_file'] = str(copy.relative_to(backup))
            manifest['files'].append(record)
        manifest['status'] = 'backed_up'
        atomic_write(manifest_path, (json.dumps(manifest, indent=2) + '\n').encode(), 0o600)
        check_plan(plan)
        for op in plan.operations:
            check_operation(op)
            absent = []
            parent = op.path.parent
            while not parent.exists():
                absent.append(parent)
                parent = parent.parent
            for directory in reversed(absent):
                directory.mkdir()
                created_dirs.append(directory)
            changed.append(op)
            atomic_write(op.path, op.after, op.after_mode if op.after_mode is not None else op.mode)
        for op in plan.operations:
            if (file_hash(op.path) != checksum(op.after) or
                    stat.S_IMODE(op.path.stat().st_mode) != (op.after_mode if op.after_mode is not None else op.mode)):
                raise OSError('Repair verification failed: ' + str(op.path))
        manifest['status'] = 'applied'
        atomic_write(manifest_path, (json.dumps(manifest, indent=2) + '\n').encode(), 0o600)
        result = {'status': 'applied', 'backup_directory': str(backup), 'changed_files': len(changed)}
        if on_applied:
            with transaction_signals(rollback=True):
                on_applied(result)
        return result
    except BaseException as exc:
        rollback_errors = []
        with transaction_signals(rollback=True):
            for op in reversed(changed):
                try:
                    restore_operation(op)
                except BaseException as rollback_exc:
                    rollback_errors.append(f'{op.path}: {rollback_exc}')
            for directory in reversed(created_dirs):
                try:
                    directory.rmdir()
                except OSError:
                    pass
            manifest.update(status='rollback_failed' if rollback_errors else 'rolled_back',
                            error=str(exc) or type(exc).__name__, rollback_errors=rollback_errors)
            try:
                atomic_write(manifest_path, (json.dumps(manifest, indent=2) + '\n').encode(), 0o600)
            except OSError:
                pass
        message = f'Repair failed. Backup: {backup}. Status: {manifest["status"]}. {exc}'
        failure = KeyboardInterrupt(message) if isinstance(exc, KeyboardInterrupt) else RuntimeError(message)
        failure.backup_directory = str(backup)
        failure.rollback_errors = rollback_errors
        raise failure from exc
