"""Confirm the public installer supplied the complete skill to each target path."""
from pathlib import Path
import hashlib, json, os

root = Path(__file__).resolve().parents[1]
home = Path.home()
paths = {
    # skills@1.7.0 uses the shared Agent Skills directory for these targets.
    'codex': home/'.agents/skills/explain',
    'claude-code': Path(os.environ.get('CLAUDE_CONFIG_DIR', home/'.claude'))/'skills/explain',
    'opencode': home/'.agents/skills/explain',
}
expected = root/'skills/explain'
report = {'scope': 'Installation and file integrity only; no model invocation', 'harnesses': {}}
for harness, directory in paths.items():
    checked = []
    for source in sorted(expected.rglob('*')):
        if not source.is_file():
            continue
        relative = source.relative_to(expected)
        installed = directory/relative
        assert installed.is_file(), f'{harness}: missing {relative}'
        assert installed.read_bytes() == source.read_bytes(), f'{harness}: differs: {relative}'
        checked.append({'file': str(relative), 'sha256': hashlib.sha256(installed.read_bytes()).hexdigest()})
    report['harnesses'][harness] = {'passed': True, 'files': checked}
(root/'cloud-installation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
