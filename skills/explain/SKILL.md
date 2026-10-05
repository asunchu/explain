---
name: explain
description: Write clear technical English for replies, documentation, procedures, and explanations. Use 80% STE by default and strict writing rules for instructions. Choose text, diagrams, interactive HTML, or narrated video when they help. Preserve code, exact quotations, and the user's requested style.
---

# Explain

Make each explanation easy to read once and understand. Start with clear words. Choose a richer format only when it helps.

This skill uses a house style inspired by ASD-STE100. It works in Codex, Claude Code, and OpenCode.

## Write clearly by default

Apply these rules to prose that people read to understand or do something. This includes replies, messages, documentation, comments, labels, and scripts.

Use **80% STE** for replies, explanations, teaching, and commit or PR text. This name means a relaxed style, not a compliance score.
Use **strict STE** for procedures, runbooks, safety text, UI copy, and error messages. The user can select either mode.

Keep the core rules in both modes:

- Give each sentence one topic. Use at most 20 words for an instruction and 25 words for a description.
- Use active voice. Write each procedure step as one command. Keep articles such as “the” and “a.”
- Use present tense for descriptions. Use past tense for completed facts. Do not change tense if that changes the truth.
- Use short, clear verbs and stable names. Define unfamiliar terms before use. Split long groups of nouns.
- Keep each paragraph on one topic, with at most six sentences. Put a needed warning before its step.

Read [RULES.md](RULES.md) and [WORDS.md](WORDS.md) when applying or checking the detailed writing rules.
In 80% mode, allow a familiar word or connective when it improves clarity. In strict mode, check every rule and word choice.
Our word guide is not the official dictionary. Claim full ASD-STE100 compliance only after checking the official rules and dictionary.
If that check is unavailable, apply the strict house rules and disclose the missing dictionary check when compliance matters.

Preserve code identifiers, commands, paths, quoted errors, legal text, third-party quotations, and the user's text unless asked to edit them.
Technical names can remain nouns. Do not rename an API or command to satisfy a word preference.
The user's requested language, voice, and layout take precedence. Do not turn uncertainty into certainty to simplify a sentence.

Before delivery, check word choice, sentence length, voice, and procedure steps. Keep this review internal unless the user requests an audit.
Do not attach a compliance report to each ordinary reply.

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
2. Apply the writing rules above to the prose, labels, captions, and narration.
3. Build a causal sequence: familiar starting point → concrete example → visible mechanism → consequence → useful takeaway. A visual should explain a relationship or change, not simply decorate narration.
4. For substantial artifacts, draft a compact storyboard with scene ID, teaching point, narration, visible objects, action, and source. Proceed within existing authorization; do not impose a new approval gate unless the user asked to review first.

## Select animation and narration

Read [VIDEO.md](VIDEO.md) for video scripts and production checks.
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

- “Why do database indexes speed up reads but slow down writes?”
- “Help me understand how software factories work.”
- “Explain transformer attention with an interactive HTML page.”
- “Make a polished 90-second video of this architecture. Use local Kokoro and Remotion.”
- “Turn this research into a narrated explainer. Hosted TTS budget: $1.”

Codex can invoke `$explain`; Claude Code can invoke `/explain`. In OpenCode, ask to use the `explain` skill. Natural-language selection is also supported when the harness makes the skill available.
