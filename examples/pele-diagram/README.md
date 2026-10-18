# Home HQ diagram

This illustrative example uses Pele 1.6.0 for layout and resvg 2.6.2 for PNG export.
The export resolves the diagram colors and loads Arial explicitly. Its PNG preserves the font across remote clients.
The page uses the same compact layout at desktop and mobile widths.

Run these commands from this directory:

```sh
npm ci --ignore-scripts --prefix ../../skills/explain/scripts/diagrams
npm ci --ignore-scripts
npm run render
```

The default font paths target macOS. `DIAGRAM_FONT_FILES` can specify other Arial files using the platform's path separator.
The export rejects missing or unusable fonts before replacing the assets.
The resvg PNG renderer and font files are separate build tools. Neither appears inside the distributable Explain skill.

Edit `architecture.mmd` to change the diagram.
The export updates the SVG and PNG assets, including the existing mobile filenames.
Inspect both exports after changing the source or font files.
