"""Check distributable files, local links, and example timing without renderer dependencies."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
import json, re, wave

root = Path(__file__).resolve().parents[1]
text = (root/'skills/explain/SKILL.md').read_text()
assert text.startswith('---\nname: explain\n') and '\ndescription: ' in text
assert len(text.split('---',2)) == 3
for link in re.findall(r'\]\(([^)]+)\)', text):
    if not urlsplit(link).scheme:
        assert (root/'skills/explain'/link).is_file(), link

class Links(HTMLParser):
    def __init__(self, path):
        super().__init__(); self.path=path
    def handle_starttag(self, tag, attrs):
        for key,value in attrs:
            if key not in ('href','src','poster') or not value: continue
            if urlsplit(value).scheme or value.startswith('#'): continue
            path=(self.path.parent/unquote(urlsplit(value).path)).resolve()
            assert path.is_relative_to(root), value
            assert path.exists(), f'{self.path}: {value}'

for path in root.rglob('*.html'):
    if 'node_modules' not in path.parts:
        Links(path).feed(path.read_text())

film=root/'examples/explain-video'
timeline=json.loads((film/'src/timeline.json').read_text())
cursor=0
for scene in timeline['scenes']:
    assert scene['start']==cursor
    with wave.open(str(film/f"public/audio/{scene['id']}.wav")) as audio:
        assert abs(audio.getnframes()/audio.getframerate()-scene['duration']/30)<.001
    end=0
    for cue in scene['captions']:
        assert end <= cue['start'] < cue['end'] <= scene['duration']
        end=cue['end']
    cursor+=scene['duration']
assert cursor == timeline['duration']
for path in root.rglob('*'):
    if any(part in ('.git','node_modules','.venv','models','__pycache__') for part in path.parts): continue
    if path.is_file() and path.suffix in ('.md','.py','.mjs','.jsx','.json','.html','.yml'):
        source=path.read_text()
        # Build strings separately so the validator does not match itself.
        assert '/'+'Users/' not in source, f'Personal path in {path}'
        assert not re.search(r'gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----',source), f'Possible credential in {path}'
assert 'window.openai' not in (root/'examples/software-factory/index.html').read_text()
print('Passed: skill references, local HTML links, scene audio/caption timing, portable paths, credential-pattern check.')
