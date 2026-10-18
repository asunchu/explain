import { access, readFile, stat, writeFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { Resvg } from '@resvg/resvg-js';
import { delimiter } from 'node:path';
import { renderDiagram } from '../../skills/explain/scripts/diagrams/render.mjs';

const source = await readFile(new URL('./architecture.mmd', import.meta.url), 'utf8');
const { svg: input } = await renderDiagram(source, { width: 360, now: Date.UTC(2026, 9, 18) });
const values = {
  '--_bg': '#ffffff', '--_fg': '#172436', '--_m': '#52627a',
  '--_l': '#5f728c', '--_s': '#f5f7fa', '--_a': '#eef2f7',
  '--_b': '#cbd3df', '--_c': '#1a4273', '--_r': '12px',
  '--_fm': 'monospace', '--pele-font': 'Arial',
};
let diagram = input;
for (let i = 0; i < 8; i++) {
  const next = diagram.replace(/var\((--[\w-]+)(?:,([^()]*))?\)/g, (match, key, fallback) => values[key] ?? fallback ?? match);
  if (next === diagram) break;
  diagram = next;
}
if (diagram.includes('var(')) throw new Error('The export contains an unresolved style variable.');
diagram = diagram.replace('<svg ', '<svg font-family="Arial" font-size="16" ')
  .replace(/<rect /g, '<rect rx="12" ')
  .replace('class="pele-edges"', 'class="pele-edges" stroke-width="1.5"');
const view = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(diagram);
if (!view) throw new Error('The diagram has no view box.');
const width = Number(view[1]) + 40;
const height = Number(view[2]) + 140;
if (width * height * 9 > 16_000_000) throw new Error('Reduce the example size before exporting PNG.');
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" font-family="Arial" fill="#172436" role="img" aria-labelledby="export-title export-desc">
<title id="export-title">Home HQ family dashboard architecture</title>
<desc id="export-desc">Apple apps supply a Mac EventKit bridge and Household API. Browsers use Tailscale. The Android frame uses the home HTTPS relay and WebView.</desc>
<rect width="${width}" height="${height}" fill="#ffffff"/>
<text x="20" y="31" font-size="24" font-weight="700">Home HQ</text>
<text x="20" y="56" font-size="14" fill="#52627a">Apple stays the source of truth.</text>
<g transform="translate(20,76)">${diagram}</g>
<text x="20" y="${height - 37}" font-size="12" fill="#52627a">The bridge checks Apple before saving completions.</text>
<text x="20" y="${height - 16}" font-size="12" fill="#6b7789">Illustrative architecture · Rendered with Pele</text>
</svg>`;
const fonts = process.env.DIAGRAM_FONT_FILES?.split(delimiter) ?? [
  '/System/Library/Fonts/Supplemental/Arial.ttf',
  '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
];
if (!fonts.length || fonts.some((file) => !file.trim())) throw new Error('Set readable Arial font files before exporting.');
try {
  await Promise.all(fonts.map(async (file) => {
    if (!(await stat(file)).isFile()) throw new Error('The font path is not a regular file.');
    await access(file, constants.R_OK);
  }));
} catch (cause) {
  throw new Error('Load readable Arial font files before exporting the diagram.', { cause });
}
const font = { fontFiles: fonts, loadSystemFonts: false, defaultFontFamily: 'Arial', sansSerifFamily: 'Arial' };
const fontProbe = new Resvg('<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40"><text x="0" y="28" font-family="Arial" font-size="20">Home HQ</text></svg>', { font });
const fontBounds = fontProbe.innerBBox();
if (!fontBounds || fontBounds.width <= 0 || fontBounds.height <= 0) throw new Error('Load a font that can draw the diagram labels.');
const renderer = new Resvg(svg, {
  font,
  fitTo: { mode: 'width', value: width * 3 },
  background: '#ffffff',
});
if (renderer.imagesToResolve().length) throw new Error('The export requires an external image.');
const png = renderer.render();
for (const name of ['architecture.svg', 'architecture-mobile.svg']) {
  await writeFile(new URL(name, import.meta.url), svg);
}
for (const name of ['architecture.png', 'architecture-mobile.png']) {
  await writeFile(new URL(name, import.meta.url), png.asPng());
}
console.log(JSON.stringify({ width, height, pngWidth: png.width, pngHeight: png.height }));
