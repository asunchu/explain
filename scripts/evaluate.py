#!/usr/bin/env python3
"""Prepare portable behavior trials and summarize evidence-backed human ratings.

This runner never calls an LLM and never grades wording with regexes.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / 'evals/cases.json'
HARNESSES = ('codex', 'claude-code', 'opencode')
STATES = ('pending', 'pass', 'fail', 'blocked')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_suite(path=SUITE):
    suite = json.loads(Path(path).read_text())
    require(suite.get('version') == 1, 'Unsupported suite version')
    cases = suite.get('cases')
    require(isinstance(cases, list) and cases, 'Suite must contain cases')
    ids = set()
    for case in cases:
        cid = case['id']
        require(isinstance(cid, str) and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', cid), 'Invalid case ID')
        require(cid not in ids, f'Duplicate case: {cid}')
        ids.add(cid)
        require(case['tier'] in ('core', 'artifact', 'media', 'discovery'), f'Unknown tier: {cid}')
        for field in ('prompt', 'setup'):
            require(isinstance(case[field], str) and case[field].strip(), f'Missing {field}: {cid}')
        require(isinstance(case['acceptable_formats'], list) and case['acceptable_formats'], f'Missing formats: {cid}')
        require(all(f in ('prose', 'diagram', 'interactive-html', 'video', 'partial') for f in case['acceptable_formats']), f'Unknown format: {cid}')
        require(case['criteria'], f'Missing criteria: {cid}')
        keys = set()
        for criterion in case['criteria']:
            key = criterion['id']
            require(isinstance(key, str) and re.fullmatch(r'[a-z0-9-]+', key), f'Invalid criterion: {cid}')
            require(key not in keys, f'Duplicate criterion: {cid}/{key}')
            require(isinstance(criterion['requirement'], str) and criterion['requirement'].strip(), f'Empty criterion: {cid}/{key}')
            keys.add(key)
    return suite


def digest_tree(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def prepare(args):
    suite = load_suite()
    cases = [c for c in suite['cases'] if args.tier == 'all' or c['tier'] == args.tier]
    if args.case:
        selected = set(args.case)
        require(selected <= {c['id'] for c in cases}, 'Unknown case or case excluded by tier')
        cases = [c for c in cases if c['id'] in selected]
    out = args.out.resolve()
    require(not out.exists(), 'Output already exists; use a new run directory')
    require(not out.is_relative_to(ROOT), 'Use a run directory outside the repository')
    out.mkdir(parents=True)
    (out / 'selection.json').write_text(json.dumps([c['id'] for c in cases]) + '\n')
    shutil.copytree(ROOT / 'skills/explain', out / 'candidate-skill')
    (out / 'suite.json').write_text(json.dumps(suite, indent=2) + '\n')
    results = {'schema_version': 1, 'harness': args.harness, 'model': args.model,
               'harness_version': args.harness_version, 'created_at': datetime.now(timezone.utc).isoformat(),
               'skill_sha256': digest_tree(out / 'candidate-skill'), 'reviewer': '', 'cases': []}
    for case in cases:
        folder = out / case['id']
        (folder / 'work').mkdir(parents=True)
        # Only the user's prompt enters the tested session. Rubrics remain outside work/.
        (folder / 'prompt.txt').write_text(case['prompt'] + '\n')
        (folder / 'review.md').write_text('# ' + case['id'] + '\n\nSetup: ' + case['setup'] +
            '\n\nAcceptable formats: ' + ', '.join(case['acceptable_formats']) + '\n\n' +
            '\n'.join('- ' + c['id'] + ': ' + c['requirement'] for c in case['criteria']) + '\n')
        results['cases'].append({'id': case['id'], 'observed_format': None, 'transcript': '',
            'criteria': {c['id']: {'status': 'pending', 'evidence': ''} for c in case['criteria']}})
    (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(f'Prepared {len(cases)} unexecuted cases in {out}')
    print('Run fresh harness sessions, retain transcripts/artifacts, then fill results.json. See evals/README.md.')


def summarize(path):
    result = json.loads(path.read_text())
    suite = load_suite(path.parent / 'suite.json')
    lookup = {c['id']: c for c in suite['cases']}
    require(result.get('schema_version') == 1, 'Unsupported result schema')
    require(result.get('harness') in HARNESSES, 'Unknown harness')
    require(result.get('model') and result.get('harness_version'), 'Model and harness version required')
    require(result.get('skill_sha256') == digest_tree(path.parent / 'candidate-skill'), 'Candidate skill changed after preparation')
    rows = result.get('cases')
    require(isinstance(rows, list) and rows, 'No results')
    seen, counts, lines = set(), Counter(), []
    for row in rows:
        cid = row['id']
        require(cid in lookup and cid not in seen, f'Unknown/duplicate result: {cid}')
        seen.add(cid)
        case = lookup[cid]
        require(set(row['criteria']) == {c['id'] for c in case['criteria']}, f'Missing/extra criteria: {cid}')
        states = []
        for key, judgment in row['criteria'].items():
            status = judgment['status']
            require(status in STATES, f'Invalid status: {cid}/{key}')
            require(status == 'pending' or (isinstance(judgment.get('evidence'), str) and judgment['evidence'].strip()), f'Evidence required: {cid}/{key}')
            states.append(status)
        if any(s in ('pass', 'fail') for s in states):
            require(isinstance(result.get('reviewer'), str) and result['reviewer'].strip(), 'Reviewer required')
            transcript = row.get('transcript')
            require(isinstance(transcript, str) and transcript.strip(), f'Transcript required: {cid}')
            file = (path.parent / transcript).resolve()
            require(file.is_relative_to(path.parent.resolve()) and file.is_file() and file.stat().st_size > 0, f'Missing or unsafe transcript path: {cid}')
        status = ('fail' if 'fail' in states else 'pending' if 'pending' in states else
                  'blocked' if 'blocked' in states else 'pass')
        if status == 'pass':
            require(row.get('observed_format') in case['acceptable_formats'], f'Unexpected format on passed case: {cid}')
        counts[status] += 1
        lines.append(f"{cid}: {status}")
    require(seen == set(json.loads((path.parent / 'selection.json').read_text())), 'Selected cases were removed or added')
    print(f"{result['harness']} | {result['model']} | {len(rows)}/{len(suite['cases'])} suite cases selected")
    print('\n'.join(lines))
    print(' '.join(f'{s}={counts[s]}' for s in STATES))
    print('Human-reviewed behavioral results; the runner validates records, not artifact quality.')
    return 1 if counts['fail'] else 2 if counts['pending'] or counts['blocked'] else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('validate', help='Validate evaluation definitions only')
    prep = sub.add_parser('prepare', help='Create fresh prompt/work directories and pending results')
    prep.add_argument('--harness', choices=HARNESSES, required=True)
    prep.add_argument('--model', required=True)
    prep.add_argument('--harness-version', required=True)
    prep.add_argument('--tier', choices=('all', 'core', 'artifact', 'media', 'discovery'), default='core')
    prep.add_argument('--case', action='append')
    prep.add_argument('--out', type=Path, required=True)
    report = sub.add_parser('report', help='Exit 0=selected cases pass, 1=fail, 2=incomplete, 3=invalid records')
    report.add_argument('results', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'validate':
            suite = load_suite()
            print(f"Valid: {len(suite['cases'])} behavior cases (not executed)")
        elif args.command == 'prepare':
            prepare(args)
        else:
            return summarize(args.results.resolve())
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f'Evaluation error: {exc}', file=sys.stderr)
        return 3


if __name__ == '__main__':
    sys.exit(main())
