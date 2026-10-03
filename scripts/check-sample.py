"""Check the Linux-rendered sample against the supplied scene timeline."""
from pathlib import Path
import json, subprocess

root=Path(__file__).resolve().parents[1]
film=root/'examples/explain-video'
video=film/'output/sample.mp4'
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]))
v=next(s for s in probe['streams'] if s['codec_type']=='video')
a=next(s for s in probe['streams'] if s['codec_type']=='audio')
scene=next(s for s in json.loads((film/'src/timeline.json').read_text())['scenes'] if s['id']=='example')
assert (v['width'],v['height'],v['avg_frame_rate'],v['codec_name']) == (1920,1080,'30/1','h264')
assert a['codec_name']=='aac'
assert abs(float(probe['format']['duration'])-scene['duration']/30)<.15
result=subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],capture_output=True,text=True)
assert result.returncode==0 and not result.stderr.strip(), result.stderr
report={'runner':'GitHub-hosted Ubuntu 24.04','sample':'cache example','durationSeconds':float(probe['format']['duration']),'resolution':'1920x1080','fps':30,'codecs':['h264','aac'],'fullDecode':'passed','scope':'Existing example rendering; not model behavior or fresh TTS synthesis'}
(root/'cloud-render.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
