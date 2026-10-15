# Produce and verify an explanation

## Select animation and narration

Read [VIDEO.md](../VIDEO.md) for video scripts and production checks.
Read [references/animation.md](animation.md) when producing animated HTML or video. Defaults:

- **Interactive HTML:** HTML/CSS/SVG plus GSAP when a timeline or morphing is useful.
- **Polished video:** Remotion with React/SVG and frame-driven motion. Add Three.js through `@remotion/three` when depth or spatial relationships help.
- **Vector teaching animations:** Motion Canvas when synchronized diagrams are the main content.
- Do not default to Manim. Use it only when explicitly requested or accepted for a specific mathematical requirement.

Read [references/tts.md](tts.md) when narration is requested:

- **No API bill / local processing:** Kokoro, if its language and available voices fit.
- **Low-cost hosted narration:** Kokoro on DeepInfra, subject to current availability and price.
- **Premium expressive narration:** audition ElevenLabs on a representative passage; quality is a listening judgment, not a guaranteed ranking.

Use the user's existing provider, voice, and budget when specified. An API key being present does not establish a spending budget. Honor existing authorization; otherwise continue free/local preparation and ask only before unapproved paid usage. Keep keys in environment variables and out of generated client code. Do not silently switch local narration to a cloud service.

## Produce and synchronize

- Work in a dedicated output folder, with editable source and pinned dependencies. Resolve reference paths relative to this skill, not the current project. Inspect the existing runtime before installing anything; keep dependencies in the artifact project or its virtual environment.
- Define typography, spacing, palette, and recurring object identities before animating. Use deliberate easing, restrained depth, and visual continuity. Introduce labels at the moment their objects matter. Avoid dense paragraphs and gratuitous camera motion.
- Generate narration by scene. Cache each result by text, provider/model, voice, and voice settings so a visual edit does not trigger another paid synthesis.
- Measure actual audio duration before finalizing scene lengths. Use timestamps or alignment for precise captions; do not manufacture word timestamps from character counts. Keep captions faithful to spoken audio when pronunciation spellings differ from display text.
- Drive video motion from frame/time, with seeded randomness. Do not rely on wall-clock animation, live scrolling, network responses, or unseeded particle motion during rendering.
- For HTML, provide keyboard controls, pause/replay, a useful reduced-motion state, and a text explanation. Load local assets when promising offline operation.
- For video, render a short representative segment before the full export. Use an MP4 with broadly supported video/audio codecs unless another format is requested. Preserve narration and subtitle files separately.

## Verify and deliver

Open the HTML and exercise its controls, or inspect rendered video frames at scene boundaries and the densest moments. Check clipping, contrast, mobile legibility where applicable, missing fonts/assets, and factual labels. Check audio duration, clipping/silence, pronunciations, and synchronization using playback where available. If listening or visual inspection is unavailable, report exactly which checks were not performed.

For video, verify container, codecs, dimensions, frame rate, duration, and presence of the audio stream using available media tools. Check captions fit their scenes and the final sentence is not cut off. Building source code alone does not verify the export.

Deliver the requested artifact, editable sources, a concise transcript/source list, and a reproduction command. State actual versus estimated narration cost and any incomplete verification. Save local previews without publishing or uploading unless the task authorizes it.
