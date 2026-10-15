#!/usr/bin/env python3
"""Run paired writing-default trials. Manual review is required; this does not grade answers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_events(text):
    events = []
    for line in text.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    return events


def command(harness, model, prompt, answer):
    if harness == 'codex':
        return ['codex', 'exec', '--json', '--ephemeral', '--skip-git-repo-check',
                '--sandbox', 'read-only', '-c', 'web_search="live"', '--model', model,
                '-o', str(answer), prompt]
    if harness == 'claude-code':
        return ['claude', '-p', '--model', model, '--output-format', 'stream-json',
                '--verbose', '--no-session-persistence', '--permission-mode', 'dontAsk',
                '--tools', 'Read,Glob,Grep,WebFetch,WebSearch,Skill',
                '--allowedTools', 'Read,Glob,Grep,WebFetch,WebSearch,Skill', '--', prompt]
    return ['opencode', 'run', '--standalone', '--model', model, '--format', 'json', prompt]


def opencode_config():
    # OpenCode V2: agent rules follow global rules. No edit or shell permission.
    rules = [{'action': '*', 'resource': '*', 'effect': 'deny'}]
    rules += [{'action': a, 'resource': '*', 'effect': 'allow'}
              for a in ('read', 'glob', 'grep', 'webfetch', 'websearch', 'skill')]
    # Skill loading can succeed while reading its references needs a second permission.
    skill_roots = [Path.home() / p for p in ('.config/opencode/skills/explain',
                   '.agents/skills/explain', '.claude/skills/explain')]
    paths = {q for p in skill_roots if p.is_dir() for q in (p.absolute(), p.resolve())}
    for path in sorted(paths):
        rules.append({'action': 'external_directory', 'resource': str(path) + '/*', 'effect': 'allow'})
    return {'agents': {'build': {'permissions': rules}}}


def run_trial(harness, model, case, directory, instructions, timeout, executable=None):
    directory.mkdir(parents=True)
    work = directory / 'work'
    work.mkdir()
    # A separate root prevents unrelated repository instructions from entering a trial.
    subprocess.run(['git', 'init', '-q', str(work)], check=True)
    name = 'CLAUDE.md' if harness == 'claude-code' else 'AGENTS.md'
    (work / name).write_text(instructions)
    for filename, content in case['fixtures'].items():
        target = (work / filename).resolve()
        if not target.is_relative_to(work.resolve()):
            raise ValueError('Fixture escapes work directory')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    if harness == 'opencode':
        (work / 'opencode.jsonc').write_text(json.dumps(opencode_config(), indent=2))
    before = {str(p.relative_to(work)): digest(p) for p in work.rglob('*')
              if p.is_file() and '.git' not in p.parts}
    cmd = command(harness, model, case['prompt'], directory / 'answer.md')
    if executable:
        cmd[0] = executable
    (directory / 'command.json').write_text(json.dumps(cmd, indent=2))
    (directory / 'prompt.txt').write_text(case['prompt'])
    env = {**os.environ, 'PWD': str(work)}
    start = time.monotonic()
    timed_out = False
    with (directory / 'trace.jsonl').open('w') as out, (directory / 'stderr.log').open('w') as err:
        process = subprocess.Popen(cmd, cwd=work, env=env, stdout=out, stderr=err,
                                   stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            code = process.returncode
    events = parse_events((directory / 'trace.jsonl').read_text())
    if harness == 'claude-code':
        answer = '\n'.join(e.get('result', '') for e in events if e.get('type') == 'result')
        (directory / 'answer.md').write_text(answer)
    elif harness == 'opencode':
        answer = '\n'.join(e.get('part', {}).get('text', '') for e in events if e.get('type') == 'text')
        (directory / 'answer.md').write_text(answer)
        ids = [e['sessionID'] for e in events if 'sessionID' in e]
        if ids:
            exported = subprocess.run(['opencode', 'session', 'export', '--standalone', ids[0]],
                                      capture_output=True, text=True, timeout=30, env=env, cwd=work)
            (directory / 'session-export.json').write_text(exported.stdout)
            (directory / 'export-stderr.log').write_text(exported.stderr)
    answer_path = directory / 'answer.md'
    after = {str(p.relative_to(work)): digest(p) for p in work.rglob('*')
             if p.is_file() and '.git' not in p.parts}
    metadata = {'harness': harness, 'requested_model': model, 'exit_code': code,
                'timeout': timed_out, 'seconds': round(time.monotonic() - start, 2),
                'has_answer': answer_path.exists() and bool(answer_path.read_text().strip()),
                'input_sha256': before, 'output_sha256': after,
                'review': {key: {'status': 'pending', 'evidence': ''} for key in case['criteria']}}
    (directory / 'execution.json').write_text(json.dumps(metadata, indent=2))
    print(json.dumps({'trial': str(directory), **{k: metadata[k] for k in ('exit_code', 'timeout', 'has_answer', 'seconds')}}), flush=True)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--harness', choices=['codex', 'claude-code', 'opencode'], required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--executable', help='Explicit CLI path when PATH resolves another installed version')
    parser.add_argument('--baseline-default', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    if args.repeats < 1 or args.timeout < 1:
        parser.error('repeats and timeout must be positive')
    out = args.out.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        parser.error('Use a new output folder outside the repository')
    baseline = args.baseline_default.read_text()
    candidate = (ROOT / 'skills/explain/CORE.md').read_text()
    suite = json.loads((ROOT / 'evals/grounding.json').read_text())
    out.mkdir(parents=True)
    (out / 'baseline.md').write_text(baseline)
    (out / 'candidate.md').write_text(candidate)
    (out / 'suite.json').write_text(json.dumps(suite, indent=2))
    (out / 'runner.py').write_bytes(Path(__file__).read_bytes())
    global_file = Path.home() / {'codex': '.codex/AGENTS.md', 'claude-code': '.claude/CLAUDE.md',
                                'opencode': '.config/opencode/AGENTS.md'}[args.harness]
    global_hash = None
    if global_file.exists():
        (out / 'global-instructions.md').write_bytes(global_file.read_bytes())
        global_hash = digest(out / 'global-instructions.md')
    executable = args.executable or {'claude-code': 'claude'}.get(args.harness, args.harness)
    version = subprocess.run([executable, '--version'], capture_output=True, text=True)
    (out / 'environment.json').write_text(json.dumps({
        'harness': args.harness, 'requested_model': args.model, 'version': version.stdout.strip(), 'executable': executable,
        'baseline_sha256': digest(out / 'baseline.md'), 'candidate_sha256': digest(out / 'candidate.md'),
        'suite_sha256': digest(out / 'suite.json'), 'repeats': args.repeats,
        'global_instructions_sha256': global_hash, 'runner_sha256': digest(out / 'runner.py'),
        'limits': 'Project instruction comparison. Existing global instructions and installed skills remain. Not a clean-room skill-discovery test. Tool policies differ by harness.'}, indent=2))
    for rep in range(1, args.repeats + 1):
        conditions = [('baseline', baseline), ('candidate', candidate)]
        if rep % 2 == 0:
            conditions.reverse()
        for case in suite['cases']:
            for condition, instructions in conditions:
                metadata = run_trial(args.harness, args.model, case,
                                     out / condition / f'repeat-{rep}' / case['id'], instructions, args.timeout, args.executable)
                # Preserve first attempts and stop on infrastructure failure; never silently retry.
                if metadata['exit_code'] or metadata['timeout'] or not metadata['has_answer']:
                    print('Stopped on infrastructure failure. Remaining trials are unrun.', flush=True)
                    return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
