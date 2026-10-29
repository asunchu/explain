"""Flag long prose for manual review; this is not a full STE validator."""
import argparse
import json
from pathlib import Path
import re


def long_sentences(text, limit=25):
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    text = re.sub(r'`[^`]+`', 'CODE', text)
    text = re.sub(r'\[([^\]]+)\]\([^\n]*?\)', r'\1', text)
    text = re.sub(r'"[^"\n]*"|“[^”\n]*”',
                  lambda m: 'QUOTE' + (m[0][-2] if m[0][-2] in '.!?' else ''), text)
    text = re.sub(r'\*\*([^*]*[.!?])\*\*', r'\1 ', text)
    findings = []
    for line in text.splitlines():
        if line.lstrip().startswith(('#', '>', '|')):
            continue
        line = re.sub(r'^\s*(?:[-*]|\d+\.)\s+', '', line)
        for sentence in re.split(r'(?<=[.!?])\s+', line):
            words = re.findall(r"[\w]+(?:['’.-][\w]+)*", sentence)
            if len(words) > limit:
                findings.append({'words': len(words), 'text': sentence.strip()})
    return findings

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--limit', type=int, default=25)
    args = parser.parse_args()
    print(json.dumps(long_sentences(args.path.read_text(), args.limit), indent=2))
