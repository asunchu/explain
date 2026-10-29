# Diagram rendering with Pele

Use Mermaid source with Pele for standard flows, relationships, and sequences.
Keep custom React/SVG for illustrations or precise animation.
Honor a user who requests Mermaid's renderer or a different drawing tool.

Pele replaces the rendering engine. It accepts Mermaid syntax and produces SVG.
The integration pins Pele 1.12.0. It does not install a global package or load a CDN.

## Render locally

Use Node.js 20 or newer. Resolve these paths from the installed Explain directory.

1. Install the locked renderer dependency.

   ```sh
   npm ci --ignore-scripts --prefix "$EXPLAIN_SKILL/scripts/diagrams"
   ```

2. Save the editable Mermaid source in the artifact project.
3. Render the diagram to a new SVG file.

   ```sh
   node "$EXPLAIN_SKILL/scripts/diagrams/render.mjs" diagram.mmd diagram.svg --width 960
   ```

4. Inspect the SVG at its intended viewing size.

`EXPLAIN_SKILL` denotes the actual skill directory. Set it before using the commands.
The command refuses to replace an existing file. Choose a new output name for another render.
Pass `--width 360` for a separate mobile layout.
The width is a layout target, not a hard ceiling. Check the reported dimensions and simplify diagrams that remain too wide.
Use `accTitle` and `accDescr` in the source for accessible descriptions.

For Gantt charts, pass `--now 2026-10-18T00:00:00Z` with the intended date.
The command reports the timestamp used. Reuse it for repeatable builds.
Keep the source and SVG together. Embed exported SVG through an `img` element when interaction is unnecessary.
An SVG image does not inherit page CSS variables. Put any required theme values in the exported asset.

## Prepare the delivery

Use a clear font, a restrained palette, and short connectors.
Show separate routes as branches when they represent different paths.
Reduce unnecessary gaps before shrinking the labels.

For remote chat previews, provide a PNG alongside the editable source and SVG.
Resolve theme variables before raster export.
Load the intended font explicitly.
Verify that it can draw the labels before replacing existing assets.
Check the exported image for visible text, arrows, and clipping at the intended viewing size.
For phone delivery, inspect a preview at 360–390 pixels wide.
Check the output in the receiving client when available.
A local browser check cannot verify every remote renderer.

The repository's [Home HQ example](https://github.com/asunchu/explain/tree/main/examples/pele-diagram) includes a reproducible PNG exporter with font checks.
Its optional resvg dependency stays in the example project, outside this skill.

For video, render the asset before building the composition.
Use Remotion for scene timing and frame-driven motion. Pele does not provide video production or narration.

## Security boundary

The wrapper accepts text and a few host-controlled settings. It does not accept parsed models, renderer configuration, or icon resolvers.
It disables links and images. These settings prevent diagram navigation and image requests.
It limits source to 20,000 characters, expanded flowchart edges to 500, and SVG output to 1,000,000 characters.
It also rejects dimensions above 16,384 pixels or an area above 16 million pixels.
Rendering runs in a disposable worker with a two-second deadline and a requested 128 MiB old-generation heap limit.
Parent Node.js heap flags can override the worker's heap setting. The deadline remains necessary.
The worker receives an empty environment. Its heap setting does not cap all process memory.
The worker is a resource boundary, not an operating-system sandbox.

Keep these policies in the wrapper. Do not expose renderer options or custom icon markup to diagram authors.
Display caught errors with `textContent` in a browser. Error text can contain diagram source.
Avoid direct `mount()` or `innerHTML` integration for untrusted source.
If an application needs live diagram editing, preserve the worker boundary and review its SVG insertion policy separately.

Recheck the package and rerun the security tests before changing the pinned version.
The dated review covers this version and integration. It does not guarantee the safety of future releases.

## Compatibility

Pele supports Mermaid syntax with its own layout. The same source can produce different spacing and edge paths.
Mermaid themes do not transfer directly. Pele uses CSS variables.
HTML labels and external Mermaid plugins have compatibility limits.
Use custom SVG when these differences prevent a clear explanation.

## Sources

- [Pele API](https://pele.run/api)
- [Pele security boundary](https://pele.run/security)
- [Pele compatibility](https://pele.run/compatibility)
- [Pele source](https://github.com/obsidianmd/pele)
