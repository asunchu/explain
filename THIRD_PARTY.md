# Third-party tools and example provenance

The MIT license covers this repository's original material. It does not relicense dependencies, speech models, or linked material. No model weights, installed packages, fonts, music, stock footage, or Codex runtime assets are bundled.

- The video uses [Remotion](https://www.remotion.dev/docs/license) under its own license. Check its eligibility and commercial terms for your use. React is MIT licensed.
- Narration was synthesized locally with [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M), voice `af_heart`, via [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx). The model card specifies Apache-2.0; the wrapper uses MIT. Model files are downloaded separately. The committed WAV files are generated speech, not model weights.
- The phonemizer uses eSpeak NG through its loader. See [eSpeak NG](https://github.com/espeak-ng/espeak-ng) for GPL licensing; it is a separately installed build dependency, not bundled here.
- FFmpeg is used as an external tool. Its license depends on build configuration; see [FFmpeg legal information](https://ffmpeg.org/legal.html).
- Other package licenses are recorded in package metadata and the pinned dependency files. Refer to each upstream distribution for its notices.
- GSAP, Motion Canvas, Three.js, and hosted TTS providers are recommendations, not included runtime components. Their terms apply when used.

The software-factory example is an original illustrative simulation informed by [Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps) and [StrongDM](https://factory.strongdm.ai/). It is not either organization's implementation or an endorsement. The skill's inspiration is linked in the README; no tweet text is reproduced.
