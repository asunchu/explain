---
name: explain
description: Turn complex topics, code, research, or model outputs into clear explanations, diagrams, interactive HTML, or polished narrated explainer videos. Use when the user asks to explain visually, animate a concept, build an explorable explanation, or make an explainer video.
---

# Explain

Make the subject easier to understand. Choose a useful medium, establish a coherent visual model, and deliver a working artifact when requested. This skill runs in Codex, OpenCode, and Claude Code using ordinary file, shell, browser, and HTTP capabilities; no particular MCP server or harness-specific tool is required.

Inspired by [Karpathy's explanation-format post](https://x.com/karpathy/status/2105819303471976479): clear writing, diagrams, interactive pages, and bespoke narrated explainers. These are options, not a mandatory escalation ladder.

## Choose the output

Honor the requested medium. Otherwise use the smallest format that resolves the understanding problem:

| Understanding problem | Output |
| --- | --- |
| Definition or short conceptual question | Concise prose, with a small example |
| Structure, relationships, or a short sequence | SVG or Mermaid diagram |
| Cause and effect, adjustable parameters, comparing scenarios | Interactive HTML with meaningful controls |
| A process over time or a story best taught through narration | Animated video with narration and captions |

Do not turn a request for recommendations or a script into an unrequested production. For ambiguous artifact requests, infer sensible defaults and state them: technically curious adult, English, local output; for video, roughly 60–90 seconds at 1080p/30 fps. Ask only when missing audience, facts, format, or budget would materially change the result.

## Build the explanation

1. Establish what the viewer should understand afterward. Inspect supplied code/data and verify unstable or disputed claims against primary sources. Keep source URLs with the project. Distinguish simplified examples from measured results.
2. Write in plain, controlled English inspired by ASD-STE100: short sentences, concrete verbs, stable names, one main idea per sentence, and terms defined before use. Preserve nuance; do not claim formal ASD-STE100 compliance.
3. Build a causal sequence: familiar starting point → concrete example → visible mechanism → consequence → useful takeaway. A visual should explain a relationship or change, not simply decorate narration.
4. For substantial artifacts, draft a compact storyboard with scene ID, teaching point, narration, visible objects, action, and source. Proceed within existing authorization; do not impose a new approval gate unless the user asked to review first.

## Select animation and narration

Read [references/animation.md](references/animation.md) when producing animated HTML or video. Defaults:

- **Interactive HTML:** HTML/CSS/SVG plus GSAP when a timeline or morphing is useful.
- **Polished video:** Remotion with React/SVG and frame-driven motion. Add Three.js through `@remotion/three` when depth or spatial relationships help.
- **Vector teaching animations:** Motion Canvas when synchronized diagrams are the main content.
- Do not default to Manim. Use it only when explicitly requested or accepted for a specific mathematical requirement.

Read [references/tts.md](references/tts.md) when narration is requested:

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

## Invocation examples

- “Use explain to explain transformer attention with an interactive HTML page.”
- “Use explain to make a polished 90-second video of this architecture. Use local Kokoro and Remotion.”
- “Use explain to turn this research into a narrated explainer. Hosted TTS budget: $1.”

Codex can invoke `$explain`; Claude Code can invoke `/explain`. In OpenCode, ask to use the `explain` skill. Natural-language selection is also supported when the harness makes the skill available.
