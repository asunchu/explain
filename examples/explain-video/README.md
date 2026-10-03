# Explain — the film

A complete narrated walkthrough of the Explain skill: learning goal, medium selection, a cache example, story structure, animation choices, local narration, synchronization, verification, and delivery.

## Outputs

- `output/explain.mp4`: 1920×1080, 30 fps, H.264/AAC, with visible captions.
- `public/audio/*.wav`: the ten scene narration files. Regeneration also writes `output/narration.wav`.
- `output/captions.srt`: passage captions timed from individually synthesized clips.
- `output/transcript.md`: readable narration.
- `output/validation.json`: technical checks and verification limitations.
- `output/clarity.png`: poster frame. Regenerate all inspection frames with `npm run stills`.

The voice is AI-generated locally with Kokoro-82M, voice `af_heart`, speed 1.02. Paid speech API usage: $0. Local compute and storage are not assigned a dollar cost. No cloud rendering or publishing is required. The final export normalizes narration loudness and includes chapter markers.

## Reproduce

From this directory after installing the dependencies below:

```sh
npm run narrate
npm run stills
npm run sample
npm run render
npm run verify
```

`npm run studio` opens the editable Remotion project. `storyboard.json` contains scene intent and narration; `src/index.jsx` contains art direction and frame-driven animation. The narration script measures clips and writes `src/timeline.json`. Unchanged clips are reused using a hash of their text and voice settings.

For a clean installation, use Node.js plus `npm ci`, Python 3.11 in `.venv`, and `uv pip install --python .venv/bin/python -r requirements.lock.txt`. Download `kokoro-v1.0.onnx` and `voices-v1.0.bin` into `models/` from the release links below. The first Remotion render may download Chrome Headless Shell. FFmpeg and ffprobe are used for final validation. Exact JS versions are in `package-lock.json`.

The narration script copies the speech phonemizer's data into a temporary short directory because the native library fails with this artifact's long absolute path. It cleans up that temporary directory when the process ends.

## Sources and scope

- Skill being demonstrated: [`skills/explain/SKILL.md`](../../skills/explain/SKILL.md). The video describes the skill's intended workflow; it does not claim a custom global system-prompt rule has been installed.
- Inspiration: [Andrej Karpathy's explanation-format post](https://x.com/karpathy/status/2105819303471976479), retrieved in the creation chat through the FxTwitter mirror after X returned HTTP 403.
- [Remotion renderer](https://www.remotion.dev/docs/renderer/render-media) and [license](https://www.remotion.dev/docs/license/pricing).
- [GSAP](https://gsap.com/) and [Motion Canvas](https://motioncanvas.io/docs/).
- [Kokoro model card](https://huggingface.co/hexgrad/Kokoro-82M), Apache-2.0 model weights.
- [Kokoro ONNX runtime](https://github.com/thewh1teagle/kokoro-onnx), MIT wrapper.
- [Model](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx) and [voices](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin).

The cache diagram is an illustrative cache-miss/cache-hit example, not a benchmark. It assumes the stored response is available for reuse; real systems also apply freshness and invalidation rules.

The moving waveform is decorative motion rather than a plot of measured amplitude. Captions use measured passage boundaries, not inferred word timestamps. No music, stock footage, remote font, or generated raster imagery is used.

## Quick start with bundled narration

Use Node.js 22+, Python 3.11, and FFmpeg/ffprobe on your PATH. These commands target macOS/Linux:

```sh
npm ci
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
npm run sample
npm run render
npm run verify
```

The existing scene audio and timeline let you render without downloading speech models. To change narration, download both model files linked above into `models/`, check them against `model-checksums.json`, then run `npm run narrate`. Dependencies keep their own licenses; see [THIRD_PARTY.md](../../THIRD_PARTY.md). Windows users must adapt the virtual-environment executable paths. No independent listening audition was performed.
