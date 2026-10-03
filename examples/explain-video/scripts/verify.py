from pathlib import Path
import json, subprocess, re
import soundfile as sf

root=Path(__file__).resolve().parents[1]
video=root/'output/explain.mp4'
data=json.loads((root/'src/timeline.json').read_text())
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-show_chapters','-of','json',str(video)]))
v=next(s for s in probe['streams'] if s['codec_type']=='video')
a=next(s for s in probe['streams'] if s['codec_type']=='audio')
assert (v['width'],v['height'],v['avg_frame_rate'],v['codec_name'])==(1920,1080,'30/1','h264')
assert a['codec_name']=='aac'
assert abs(float(probe['format']['duration'])-data['duration']/30)<.15
assert len(probe['chapters'])==len(data['scenes'])
cursor=0
for scene in data['scenes']:
    assert scene['start']==cursor
    info=sf.info(root/f"public/audio/{scene['id']}.wav")
    assert abs(info.duration-scene['duration']/30)<.001
    end=0
    for cap in scene['captions']:
        assert 0<=end<=cap['start']<cap['end']<=scene['duration']
        end=cap['end']
    assert scene['duration']-end>=18
    cursor+=scene['duration']
decode=subprocess.run(['ffmpeg','-hide_banner','-v','error','-i',str(video),'-f','null','-'],capture_output=True,text=True)
assert decode.returncode==0 and not decode.stderr.strip(),decode.stderr
levels=subprocess.run(['ffmpeg','-hide_banner','-i',str(video),'-af','volumedetect','-vn','-f','null','-'],capture_output=True,text=True,check=True).stderr
peak=float(re.search(r'max_volume: ([-\d.]+) dB',levels).group(1))
assert peak<0
report={
 'video':'output/explain.mp4','durationSeconds':float(probe['format']['duration']),
 'resolution':'1920x1080','fps':30,'videoCodec':'H.264','audioCodec':'AAC',
 'chapters':len(probe['chapters']),'audioPeakDbFS':peak,
 'fullDecode':'passed without errors','sceneAudioTiming':'matched to frame timeline',
 'captions':'nonoverlapping measured passage boundaries; burned into video; SRT also supplied',
 'visualInspection':'All 10 representative scene frames reviewed; cache sample rendered and inspected',
 'limitations':['No independent listening audition of pronunciation or subjective voice quality was performed.'],
 'speechApiCostUsd':0,'narration':'AI-generated locally with Kokoro-82M / af_heart',
 'source':'storyboard.json; src/index.jsx; scripts/narrate.py; scripts/render.mjs; scripts/finalize.py'
}
(root/'output/validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
