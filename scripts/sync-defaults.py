#!/usr/bin/env python3
"""Copy the shared core into a selected instruction file, preserving other text."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from loading import routing
START = '<!-- explain-writing-default:start -->'
END = '<!-- explain-writing-default:end -->'

def merge(existing, core):
    if existing.count(START) != existing.count(END) or existing.count(START) > 1:
        raise ValueError('Expected zero or one complete default block')
    block = START + '\n' + core.strip() + '\n' + END
    if START in existing:
        a, b = existing.index(START), existing.index(END)
        if b < a:
            raise ValueError('Default block markers are reversed')
        return existing[:a] + block + existing[b + len(END):]
    return existing.rstrip() + ('\n\n' if existing.strip() else '') + block + '\n'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--skill-path', type=Path, help='Installed skill directory for automatic artifact routing')
    args = parser.parse_args()
    core = (Path(__file__).resolve().parents[1] / 'skills/explain/CORE.md').read_text()
    if args.skill_path:
        installed = args.skill_path.expanduser().absolute()
        if not (installed / 'SKILL.md').is_file():
            parser.error('The skill path must contain SKILL.md')
        core += '\n' + routing(installed)
    path = args.destination.expanduser()
    old = path.read_text() if path.exists() else ''
    result = merge(old, core)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result)
    print(path)
