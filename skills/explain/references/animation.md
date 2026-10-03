# Animation choices

Selection guidance checked 2026-10-03. Check current APIs and licenses when starting a production. These are creative recommendations, not a benchmark ranking.

| Tool | Choose it for | Practical tradeoff |
| --- | --- | --- |
| Remotion + React/SVG | Default polished video: typography, UI walkthroughs, diagrams, charts, compositing, synchronized audio | A video composition system; visuals still need intentional design |
| GSAP + HTML/SVG | Interactive explainers, scroll narratives, path morphs, choreographed transitions | Browser playback does not by itself produce a deterministic MP4 |
| Motion Canvas | Technical vector explanations, algorithm traces, diagrams synchronized to narration | More specialized than a general video editor |
| Three.js through Remotion's integration | Spatial systems, dimensional diagrams, cameras, lighting, particles | More rendering cost and complexity; use 3D only when it improves understanding |

## Art direction

“Spruced up” should mean a consistent visual system and purposeful movement. Start with a restrained palette, clear type hierarchy, generous spacing, and one dominant visual per beat. Keep the same entity's color and shape across scenes. Morph a familiar object into its next state instead of repeatedly replacing the whole screen. Use depth, highlights, and particles to show a mechanism, not as wallpaper.

For 1080p video, preview body labels around 32–44 px and keep essential content comfortably inside the frame; adjust based on the actual viewing size. Reserve room for captions. Narration explains the mechanism while the screen supplies short labels and visible evidence. Hold the completed visual long enough to process it.

## Rendering invariants

In Remotion, compute motion using `useCurrentFrame()`, interpolation, and springs. For Three.js, use `@remotion/three` and frame-driven state rather than React Three Fiber's autonomous `useFrame` loop. The same frame must render identically when reached by playback, scrubbing, or out-of-order rendering.

For GSAP browser explainers, expose play/pause/restart and seek where useful. If exporting video, use a paused timeline driven by the renderer's timestamp, await asset/font readiness, and render deterministic frames. A normal screen recording is a fallback with different reproducibility guarantees; describe it honestly.

Use a lockfile and matching Remotion package versions. Render locally first. Do not create a cloud-rendering account or deploy infrastructure as a side effect of choosing an animation library.

## Primary sources

- [Remotion](https://www.remotion.dev/) and [license/pricing](https://www.remotion.dev/docs/license/pricing): the listed free license covers individuals and companies of up to three people, subject to terms. Larger organizations and collaborations require reviewing paid licensing. Do not describe Remotion as universally free/open source.
- [Remotion ThreeCanvas](https://www.remotion.dev/docs/three-canvas): frame-synchronized Three.js integration.
- [GSAP](https://gsap.com/): timelines and animation for UI, SVG, text, and WebGL.
- [Motion Canvas introduction](https://motioncanvas.io/docs/): free, open-source TypeScript vector animation with a preview editor.
- [Motion Canvas audio](https://motion-canvas.io/docs/media/): narration track configuration.
