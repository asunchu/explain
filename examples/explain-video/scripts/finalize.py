from pathlib import Path
import json, subprocess
import numpy as np
import soundfile as sf

root=Path(__file__).resolve().parents[1]
data=json.loads((root/'src/timeline.json').read_text())
audio=[]
for scene in data['scenes']:
    samples,sr=sf.read(root/f"public/audio/{scene['id']}.wav")
    assert sr==24000
    audio.append(samples)
sf.write(root/'output/narration.wav',np.concatenate(audio),24000,subtype='PCM_16')
meta=[';FFMETADATA1','title=Explain — how the skill works','comment=AI-generated narration: local Kokoro af_heart. Created with Remotion.']
for scene in data['scenes']:
    meta.extend(['[CHAPTER]','TIMEBASE=1/30',f"START={scene['start']}",f"END={scene['start']+scene['duration']}",f"title={scene['title']}"])
(root/'output/chapters.ffmeta').write_text('\n'.join(meta)+'\n')
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error',
 '-i',str(root/'output/explain-raw.mp4'),'-i',str(root/'output/narration.wav'),
 '-i',str(root/'output/chapters.ffmeta'),'-map','0:v:0','-map','1:a:0','-map_metadata','2','-map_chapters','2',
 '-c:v','copy','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-ar','48000','-c:a','aac','-b:a','160k',
 '-movflags','+faststart',str(root/'output/explain.mp4')],check=True)
print('Final export: output/explain.mp4')
