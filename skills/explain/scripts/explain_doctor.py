#!/usr/bin/env python3
"""Inspect Explain installations; repair only with --fix and verified backups."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
sys.dont_write_bytecode = True

from explain_loading import routing

DEFAULT_REFERENCE = Path(__file__).resolve().parents[1]
HARNESSES = ('codex', 'claude-code', 'opencode')
SKIP = {'.git', 'node_modules', '.venv', 'models', '__pycache__', '.DS_Store'}
START = '<!-- explain-writing-default:start -->'
END = '<!-- explain-writing-default:end -->'


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(directory):
    """Hash package files only; dependency folders and caches are not the package."""
    files, errors = {}, []
    def visit(folder, ancestors):
        try:
            resolved = folder.resolve(strict=True)
            if resolved in ancestors:
                raise ValueError('Directory symlink cycle')
            for path in sorted(folder.iterdir()):
                if path.name in SKIP or path.suffix == '.pyc':
                    continue
                relative = str(path.relative_to(directory))
                try:
                    if path.is_dir():
                        visit(path, ancestors | {resolved})
                    elif path.is_file():
                        files[relative] = file_hash(path)
                    else:
                        errors.append({'file': relative, 'error': 'Not a regular file or directory'})
                except (OSError, RuntimeError, ValueError) as exc:
                    errors.append({'file': relative, 'error': str(exc)})
        except (OSError, RuntimeError, ValueError) as exc:
            errors.append({'file': str(folder.relative_to(directory)), 'error': str(exc)})
    visit(directory, set())
    return files, errors


def fingerprint(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def declared_pele(directory):
    try:
        path = directory / 'scripts/diagrams/package.json'
        if not path.is_file():
            return None
        manifest = json.loads(path.read_text())
        dependencies = manifest.get('dependencies') if isinstance(manifest, dict) else None
        value = dependencies.get('pele') if isinstance(dependencies, dict) else None
        return value if isinstance(value, str) else None
    except (OSError, ValueError):
        return None


def inspect_installation(path, expected):
    result = {'path': str(path), 'resolved': None, 'state': 'unreadable'}
    try:
        result['resolved'] = str(path.resolve(strict=True))
        if not path.is_dir():
            result['state'] = 'not_directory'
            return result
        result['kind'] = 'directory'
        files, errors = inventory(path)
        result.update(fingerprint=fingerprint(files), missing=sorted(expected.keys() - files.keys()),
                      changed=sorted(k for k in expected.keys() & files.keys() if expected[k] != files[k]),
                      extra=sorted(files.keys() - expected.keys()), errors=errors)
        result['state'] = ('unreadable' if errors else 'different' if
                           result['missing'] or result['changed'] or result['extra'] else 'match')
        result['pele'] = declared_pele(path)
    except FileNotFoundError:
        result['state'] = 'broken_link' if path.is_symlink() else 'missing'
    except (OSError, RuntimeError, ValueError) as exc:
        result['error'] = str(exc)
    return result


def inspect_defaults(path, core):
    result = {'path': str(path), 'state': 'missing', 'routing': 'absent', 'route_content': 'absent', 'routes': []}
    try:
        if not stat.S_ISREG(path.stat().st_mode):
            result['state'] = 'unreadable'
            result['error'] = 'Not a regular instruction file'
            return result
        text = path.read_text()
    except FileNotFoundError:
        if path.is_symlink():
            result['state'] = 'broken_link'
        return result
    except (OSError, UnicodeError) as exc:
        result.update(state='unreadable', error=str(exc))
        return result
    result['sha256'] = hashlib.sha256(text.encode()).hexdigest()
    if START not in text and END not in text:
        result['state'] = 'unmanaged'
        return result
    if text.count(START) != 1 or text.count(END) != 1 or text.index(END) < text.index(START):
        result['state'] = 'invalid_markers'
        return result
    block = text.split(START, 1)[1].split(END, 1)[0].strip()
    writing, separator, router = block.partition('\n## Explanation artifacts')
    result['state'] = 'match' if writing.strip() == core.strip() else 'different'
    result['block_sha256'] = hashlib.sha256(block.encode()).hexdigest()
    if separator:
        # This recognizes the router emitted by sync-defaults.py, not arbitrary prose.
        targets = re.findall(r'`([^`\n]+/SKILL\.md)`', router)
        result['routing'] = 'present' if targets else 'unrecognized'
        result['route_content'] = ('match' if len(targets) == 1 and
                                   ('## Explanation artifacts' + router).strip() == routing(Path(targets[0]).parent).strip()
                                   else 'different')
        for target in dict.fromkeys(targets):
            entry = Path(target).expanduser()
            if not entry.is_absolute():
                result['routes'].append({'path': target, 'state': 'relative_unresolved'})
                continue
            try:
                resolved = entry.resolve(strict=True)
                result['routes'].append({'path': target, 'resolved': str(resolved),
                                         'state': 'exists' if resolved.is_file() else 'missing'})
            except (OSError, RuntimeError) as exc:
                result['routes'].append({'path': target, 'state': 'missing', 'error': str(exc)})
    return result


def project_ancestors(project):
    """Stop at the closest worktree root, including .git files in linked worktrees."""
    for directory in (project, *project.parents):
        yield directory
        if (directory / '.git').exists():
            break


def locations(home, project, env, global_only=False):
    codex = Path(env.get('CODEX_HOME', home / '.codex')).expanduser().absolute()
    claude = Path(env.get('CLAUDE_CONFIG_DIR', home / '.claude')).expanduser().absolute()
    config = Path(env.get('XDG_CONFIG_HOME', home / '.config')).expanduser().absolute()
    opencode = config / 'opencode'
    roots = {'codex': [home / '.agents/skills', codex / 'skills'],
             'claude-code': [claude / 'skills'],
             'opencode': [opencode / 'skills', claude / 'skills', home / '.agents/skills']}
    override = codex / 'AGENTS.override.md'
    try:
        use_override = override.stat().st_size > 0 or not override.is_file()
    except FileNotFoundError:
        use_override = override.is_symlink()
    except OSError:
        use_override = True
    defaults = {'codex': [override if use_override else codex / 'AGENTS.md'], 'claude-code': [claude / 'CLAUDE.md'],
                'opencode': [opencode / 'AGENTS.md']}
    if env.get('OPENCODE_CONFIG_DIR'):
        custom = Path(env['OPENCODE_CONFIG_DIR']).expanduser().absolute()
        roots['opencode'].append(custom / 'skills')
        defaults['opencode'].append(custom / 'AGENTS.md')
    for directory in (() if global_only else project_ancestors(project)):
        roots['codex'].append(directory / '.agents/skills')
        roots['claude-code'].append(directory / '.claude/skills')
        roots['opencode'].extend(directory / p for p in ('.opencode/skills', '.claude/skills', '.agents/skills'))
        for harness, names in {'codex': ('AGENTS.md', 'AGENTS.override.md'),
                               'claude-code': ('CLAUDE.md', '.claude/CLAUDE.md', 'CLAUDE.local.md'),
                               'opencode': ('AGENTS.md', 'CLAUDE.md')}.items():
            defaults[harness].extend(directory / name for name in names)
    return roots, defaults


def find_candidates(root):
    """Inspect immediate skill folders, including custom folders named by frontmatter."""
    try:
        if not root.exists() and not root.is_symlink():
            return [], None
        children = {p.name: p for p in root.iterdir()}
        found = []
        for name, child in sorted(children.items()):
            if name == 'explain':
                found.append(child)  # Also retain incomplete or broken installations.
            elif not name.startswith('.'):
                try:
                    entry = child / 'SKILL.md'
                    if not entry.is_file():
                        continue
                    text = entry.read_text()
                    frontmatter = text.split('---', 2)[1] if text.startswith('---\n') else ''
                    if re.search(r'^name:\s*[\'\"]?explain[\'\"]?\s*$', frontmatter, re.M):
                        found.append(child)
                except (OSError, UnicodeError):
                    continue
        return found, None
    except (OSError, RuntimeError) as exc:
        return [], str(exc)


def build_report(reference, project, home=None, env=None, harnesses=HARNESSES, extra_paths=(), global_only=False):
    home = (home or Path.home()).absolute()
    env = os.environ if env is None else env
    reference, project = reference.absolute(), project.absolute()
    if not project.is_dir() or not (reference / 'SKILL.md').is_file():
        raise ValueError('The project must be a directory and the reference must contain SKILL.md')
    expected, errors = inventory(reference)
    if errors:
        raise ValueError('Cannot read all reference files: ' + json.dumps(errors))
    core = (reference / 'CORE.md').read_text()
    roots, default_paths = locations(home, project, env, global_only)
    report = {'schema_version': 1, 'scope': 'Local installation comparison; no proof of active loading or behavior',
              'reference': {'path': str(reference), 'fingerprint': fingerprint(expected), 'files': len(expected), 'pele': declared_pele(reference)},
              'project': str(project), 'harnesses': {}, 'installations': {}, 'aliases': {}, 'findings': [],
              'limits': ['Checks standard local paths, legacy Codex paths, supplied paths, and marked routers.',
                         'Does not inspect plugin stores, enterprise policy, cloud skills, or session-added directories.',
                         'Does not determine precedence, enabled state, or the files loaded by a running harness.',
                         'Unmarked writing rules are reported as unmanaged, not compared as Explain defaults.',
                         'Fingerprints identify content; installed release versions are not inferred.',
                         'The default reference is the copy running this tool, not the latest release. Supply --reference to compare another source.']}
    def finding(code, **fields):
        report['findings'].append({'code': code, **fields})
    def add(path):
        key = str(path)
        if key not in report['installations']:
            report['installations'][key] = inspect_installation(path, expected)
        return key
    for harness in dict.fromkeys(harnesses):
        found, searched = [], []
        for root in dict.fromkeys(roots[harness]):
            candidates, error = find_candidates(root)
            searched.append({'path': str(root), 'error': error})
            if error:
                finding('scan_error', harness=harness, path=str(root), error=error)
            found.extend(add(path) for path in candidates)
        found.extend(add(Path(path).expanduser().absolute()) for path in extra_paths)
        instructions = [inspect_defaults(path, core) for path in dict.fromkeys(default_paths[harness])]
        for default in instructions:
            if Path(default['path']).name == 'AGENTS.override.md' and default['state'] == 'unmanaged':
                finding('defaults_override_unmanaged', harness=harness, path=default['path'])
            if default['state'] in ('different', 'invalid_markers', 'unreadable', 'broken_link'):
                finding('defaults_' + default['state'], harness=harness, path=default['path'])
            for route in default['routes']:
                if route['state'] == 'exists':
                    found.append(add(Path(route['path']).parent))
                else:
                    finding('route_' + route['state'], harness=harness, path=route['path'])
            if default['route_content'] == 'different':
                finding('route_content_different', harness=harness, path=default['path'])
        found = list(dict.fromkeys(found))
        targets = {report['installations'][key]['resolved'] for key in found
                   if report['installations'][key].get('kind') == 'directory'}
        if not found:
            finding('installation_not_found', harness=harness)
        if len(targets) > 1:
            finding('multiple_copies', harness=harness, targets=sorted(targets))
        report['harnesses'][harness] = {'searched': searched, 'candidates': found,
                                         'distinct_targets': len(targets), 'defaults': instructions}
    seen = set()
    for key, installation in report['installations'].items():
        target = installation['resolved'] or key
        if installation.get('kind') == 'directory':
            report['aliases'].setdefault(target, []).append(key)
        if installation['state'] != 'match' and target not in seen:
            finding('installation_' + installation['state'], path=key)
        seen.add(target)
    report['ok'] = not report['findings']
    return report


def format_text(report):
    lines = ['Explain doctor', 'Reference: ' + report['reference']['path'],
             'Content fingerprint: ' + report['reference']['fingerprint'],
             'Pele dependency (declared): ' + str(report['reference']['pele'] or 'unknown'),
             'Project: ' + report['project'], report['scope']]
    for harness, data in report['harnesses'].items():
        lines.append(f"\n{harness}: {data['distinct_targets']} distinct target(s)")
        for key in data['candidates']:
            item = report['installations'][key]
            lines.append(f"  {item['state']}: {key}")
            if item['resolved'] and item['resolved'] != key:
                lines.append('    -> ' + item['resolved'])
        for default in data['defaults']:
            if default['state'] != 'missing':
                lines.append(f"  Defaults {default['state']}: {default['path']} (routing: {default['routing']}; content: {default['route_content']})")
    for target, aliases in report['aliases'].items():
        if len(aliases) > 1:
            lines.append('\nShared installation: ' + target)
            lines.extend('  alias: ' + alias for alias in aliases)
    seen = set()
    for key, item in report['installations'].items():
        target = item['resolved'] or key
        if item['state'] == 'match' or target in seen:
            continue
        seen.add(target)
        lines.append('\nDifferences: ' + key)
        if item.get('fingerprint'):
            lines.append('  Content fingerprint: ' + item['fingerprint'])
            lines.append('  Pele dependency (declared): ' + str(item.get('pele') or 'unknown'))
        for category in ('changed', 'missing', 'extra'):
            for name in item.get(category, []):
                lines.append(f'  {category}: {name}')
        for error in item.get('errors', []):
            lines.append('  read error: ' + error['file'])
    lines.append(f"\nFindings: {len(report['findings'])}")
    for item in report['findings']:
        subject = ' '.join(item[key] for key in ('harness', 'path') if key in item)
        lines.append('  ' + item['code'] + ': ' + subject)
    if 'repair' in report:
        repair = report['repair']
        lines.append('\nRepair: ' + repair['status'])
        for action in repair.get('plan', {}).get('actions', []):
            lines.append('  ' + action['action'] + ' ' + action['kind'] + ': ' + action['path'])
        for blocker in repair.get('plan', {}).get('blockers', []):
            lines.append('  Blocked: ' + blocker)
        for note in repair.get('plan', {}).get('notes', []):
            lines.append('  Note: ' + note)
        if repair.get('backup_directory'):
            lines.append('  Backup: ' + repair['backup_directory'])
        if 'changed_files' in repair:
            lines.append('  Changed files: ' + str(repair['changed_files']))
    lines.append('\nLimits: ' + ' '.join(report['limits']))
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, default=DEFAULT_REFERENCE, help='Source skill directory; defaults to the copy running this tool, not the latest release')
    parser.add_argument('--project', type=Path, default=Path.cwd(), help='Project context for ancestor inspection')
    parser.add_argument('--harness', action='append', choices=HARNESSES, help='Check only selected harnesses')
    parser.add_argument('--skill-path', action='append', type=Path, default=[], help='Also inspect a custom skill directory')
    parser.add_argument('--json', action='store_true', help='Print the complete report as JSON')
    parser.add_argument('--global-only', action='store_true', help='Check global locations without project instructions')
    parser.add_argument('--fix', action='store_true', help='Repair installed files and existing marked defaults with backups')
    parser.add_argument('--dry-run', action='store_true', help='Preview --fix without writing files or backups')
    parser.add_argument('--backup-dir', type=Path, help='Parent directory for private per-run backups')
    args = parser.parse_args(argv)
    if args.dry_run and not args.fix:
        parser.error('--dry-run requires --fix')
    if args.backup_dir and not args.fix:
        parser.error('--backup-dir requires --fix')
    try:
        report = build_report(args.reference.expanduser(), args.project.expanduser(),
                              harnesses=args.harness or HARNESSES, extra_paths=args.skill_path, global_only=args.global_only)
    except (OSError, ValueError, RuntimeError) as exc:
        print('Explain doctor: ' + str(exc), file=sys.stderr)
        return 2
    if args.fix:
        from explain_repair import apply_plan, build_plan
        try:
            plan = build_plan(report)
            summary = plan.summary()
            result = {'status': 'blocked' if plan.blockers else 'dry_run', 'plan': summary}
            if not plan.blockers and not args.dry_run:
                state = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state')
                result.update(apply_plan(plan, args.backup_dir or state / 'explain/backups'))
                report = build_report(args.reference.expanduser(), args.project.expanduser(),
                                      harnesses=args.harness or HARNESSES, extra_paths=args.skill_path, global_only=args.global_only)
            report['repair'] = result
        except (OSError, ValueError, RuntimeError, KeyboardInterrupt) as exc:
            report['repair'] = {'status': 'failed', 'error': str(exc)}
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print('Explain repair: ' + str(exc), file=sys.stderr)
            return 130 if isinstance(exc, KeyboardInterrupt) else 2
    print(json.dumps(report, indent=2) if args.json else format_text(report))
    if args.fix and args.dry_run:
        return 2 if report['repair']['status'] == 'blocked' else 0
    if args.fix and report['repair']['status'] == 'blocked':
        return 2
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
