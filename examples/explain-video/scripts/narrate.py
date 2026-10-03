from pathlib import Path
import hashlib, json, math, os, tempfile, shutil
import espeakng_loader
# espeak's native path handling fails for this long artifact directory.
# A temporary copy keeps the resolved data path short on macOS.
data_temp = tempfile.TemporaryDirectory(prefix='explain-tts-', dir=None)
data_path = Path(data_temp.name)/'espeak-ng-data'
shutil.copytree(espeakng_loader.get_data_path(), data_path)
os.environ['ESPEAK_DATA_PATH'] = str(data_path)
os.environ['PHONEMIZER_ESPEAK_DATA_PATH'] = str(data_path)
os.environ['PHONEMIZER_ESPEAK_LIBRARY'] = espeakng_loader.get_library_path()
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
from kokoro_onnx.config import EspeakConfig

ROOT = Path(__file__).resolve().parents[1]
(ROOT/'public/audio').mkdir(parents=True, exist_ok=True)
(ROOT/'output').mkdir(exist_ok=True)
FPS = 30
VOICE = 'af_heart'
SPEED = 1.02
scenes = json.loads((ROOT / 'storyboard.json').read_text())
engine = Kokoro(str(ROOT/'models/kokoro-v1.0.onnx'), str(ROOT/'models/voices-v1.0.bin'), espeak_config=EspeakConfig(data_path=str(data_path)))
cursor = 0
captions = []
full = []
transcript = ['# Explain — how the skill works', '', 'Narration: local Kokoro, af_heart. AI-generated voice.', '']
for scene in scenes:
    scene['start'] = cursor
    local_cursor = 18
    chunks = [np.zeros(14400, dtype=np.float32)]
    scene['captions'] = []
    transcript.extend(['## '+scene['chapter'], ''])
    for text in scene['lines']:
        digest = hashlib.sha256(json.dumps([text, VOICE, SPEED, 'kokoro-v1.0']).encode()).hexdigest()[:20]
        path = ROOT/'public/audio'/f'{digest}.wav'
        if path.exists():
            samples, sr = sf.read(path)
        else:
            samples, sr = engine.create(text, voice=VOICE, speed=SPEED, lang='en-us')
            sf.write(path, samples, sr, subtype='PCM_16')
        assert sr == 24000
        frames = math.ceil(len(samples)/sr*FPS)
        padded = np.pad(samples, (0, frames*800-len(samples)))
        display = text.replace('G sap', 'GSAP').replace('Frame based', 'Frame-based')
        cue = {'text':display, 'start':local_cursor, 'end':local_cursor+frames}
        scene['captions'].append(cue)
        captions.append({'text':display,'start':cursor+local_cursor,'end':cursor+local_cursor+frames})
        chunks.extend([padded, np.zeros(4800)])
        local_cursor += frames+6
        transcript.append(display)
    chunks.append(np.zeros(14400))
    scene['duration'] = local_cursor+18
    scene_audio = np.concatenate(chunks)
    assert len(scene_audio)==scene['duration']*800
    sf.write(ROOT/'public/audio'/f"{scene['id']}.wav", scene_audio, 24000, subtype='PCM_16')
    full.append(scene_audio)
    cursor += scene['duration']
    transcript.append('')
    print(scene['id'], round(scene['duration']/FPS,2), 'seconds', flush=True)

data={'fps':FPS,'duration':cursor,'scenes':scenes,'voice':VOICE,'provider':'local Kokoro ONNX','apiCostUsd':0}
(ROOT/'src/timeline.json').write_text(json.dumps(data,indent=2))
(ROOT/'output/transcript.md').write_text('\n'.join(transcript))
sf.write(ROOT/'output/narration.wav',np.concatenate(full),24000,subtype='PCM_16')
def stamp(frame):
    ms=round(frame/FPS*1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
(ROOT/'output/captions.srt').write_text('\n\n'.join(f"{i+1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}" for i,c in enumerate(captions))+'\n')
print('Total seconds:',cursor/FPS,flush=True)
