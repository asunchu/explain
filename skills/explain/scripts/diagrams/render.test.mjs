import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { renderDiagram, MAX_SOURCE_CHARS } from './render.mjs';

const clock = { now: Date.UTC(2026, 9, 18) };
const run = promisify(execFile);

test('renders accessible SVG with repeatable output', async () => {
  const source = 'flowchart LR\naccTitle: Apple remains authoritative\nA[Apple] --> B[Bridge] --> C[Dashboard]';
  const first = await renderDiagram(source, clock);
  const second = await renderDiagram(source, clock);
  assert.equal(first.svg, second.svg);
  assert.equal(first.type, 'flowchart');
  assert.match(first.svg, /<title[^>]*>Apple remains authoritative<\/title>/);
});

test('adapts a wide diagram to a narrow container', async () => {
  const source = 'flowchart LR\nA[Apple Calendar] --> B[Mac EventKit bridge] --> C[Household API] --> D[Android dashboard]';
  const wide = await renderDiagram(source, { ...clock, width: 1200 });
  const narrow = await renderDiagram(source, { ...clock, width: 360 });
  assert.notEqual(wide.svg, narrow.svg);
  assert.ok(narrow.height > wide.height);
  assert.ok(narrow.width <= 360);
});

test('keeps labels as text and blocks navigation', async () => {
  const result = await renderDiagram('flowchart LR\nA["<script>alert(1)</script>"] --> B[Safe]\nclick B "https://example.invalid/track"', clock);
  assert.doesNotMatch(result.svg, /<script\b|<a\b|\shref=/i);
  assert.deepEqual(result.links, []);
});

test('chooses contrasting labels for light and dark custom fills', async () => {
  const { svg } = await renderDiagram('flowchart LR\nA[Light] --> B[Dark]\nstyle A fill:#ffffff\nstyle B fill:#000000', clock);
  assert.match(svg, /<text[^>]*fill="var\(--pele-fg-on-light,[^"]+\)"[^>]*>Light<\/text>/);
  assert.match(svg, /<text[^>]*fill="var\(--pele-fg-on-dark,[^"]+\)"[^>]*>Dark<\/text>/);
});

test('keeps a custom group fill opaque', async () => {
  const { svg } = await renderDiagram('flowchart LR\nsubgraph G[Group]\nA --> B\nend\nstyle G fill:#fde68a', clock);
  const group = svg.match(/<g class="pele-cluster"[^>]*>([\s\S]*?)<\/g>/)?.[1];
  assert.ok(group, 'The group must be present.');
  assert.match(group, /fill:#fde68a/);
  assert.doesNotMatch(group, /(?:fill-)?opacity(?:=|:)"?0\.5/);
});

test('blocks remote image output and ignores attempts to change host policy', async () => {
  const source = '%%{init: {"links":true,"images":true,"limit":999999,"maxEdges":999999}}%%\nflowchart LR\nA@{ img: "https://example.invalid/track", label: "Image", h: 60 }\nclick A "https://example.invalid/link"';
  const result = await renderDiagram(source, clock);
  assert.doesNotMatch(result.svg, /<image\b|<a\b|example\.invalid/i);
  assert.deepEqual(result.links, []);
});

test('rejects oversized source and pre-parsed models before loading the renderer', async () => {
  await assert.rejects(renderDiagram('flowchart LR\n' + 'A'.repeat(MAX_SOURCE_CHARS)), /characters/);
  await assert.rejects(renderDiagram({ type: 'flowchart' }), /source as text/);
});

test('enforces the edge cap on compact expansion', async () => {
  const left = Array.from({ length: 23 }, (_, i) => `a${i}`).join(' & ');
  const right = Array.from({ length: 23 }, (_, i) => `b${i}`).join(' & ');
  await assert.rejects(renderDiagram(`flowchart LR\n${left} --> ${right}`, clock), /500|edges|limit/i);
});

test('enforces the output cap under the source and edge limits', async () => {
  const longId = 'A'.repeat(3_000);
  const targets = Array.from({ length: 500 }, (_, i) => `n${i}`).join(' & ');
  await assert.rejects(renderDiagram(`flowchart LR\n${longId} --> ${targets}`, clock), /output.*limit/i);
});

test('rejects giant dimensions from compact block source', async () => {
  await assert.rejects(renderDiagram('block-beta\ncolumns 1\nspace:100000', clock), /dimensions/);
});

test('terminates a worker at its deadline', async () => {
  await assert.rejects(renderDiagram('flowchart LR\nA --> B', { ...clock, timeoutMs: 1 }), /deadline/);
});

test('rejects unsupported input without exposing an HTML error sink', async () => {
  await assert.rejects(renderDiagram('<img src=x onerror=alert(1)>', clock), /diagram type/i);
});

test('CLI writes SVG and preserves an existing output after failure', async () => {
  const folder = await mkdtemp(join(tmpdir(), 'explain-pele-'));
  try {
    const input = join(folder, 'diagram.mmd');
    const output = join(folder, 'diagram.svg');
    await writeFile(input, 'flowchart LR\nA --> B');
    const cli = fileURLToPath(new URL('./render.mjs', import.meta.url));
    await run(process.execPath, [cli, input, output]);
    const original = await readFile(output, 'utf8');
    assert.match(original, /^<svg /);
    await assert.rejects(run(process.execPath, [cli, input, output]), /EEXIST/);
    await writeFile(input, 'invalid diagram');
    await assert.rejects(run(process.execPath, [cli, input, output]));
    assert.equal(await readFile(output, 'utf8'), original);
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
});

test('CLI rejects oversized and invalid UTF-8 files', async () => {
  const folder = await mkdtemp(join(tmpdir(), 'explain-pele-input-'));
  try {
    const input = join(folder, 'diagram.mmd');
    const output = join(folder, 'diagram.svg');
    const cli = fileURLToPath(new URL('./render.mjs', import.meta.url));
    await writeFile(input, Buffer.alloc(80_001, 65));
    await assert.rejects(run(process.execPath, [cli, input, output]), /bytes/);
    await writeFile(input, Buffer.from([0xc3, 0x28]));
    await assert.rejects(run(process.execPath, [cli, input, output]), /encoded data/i);
    await assert.rejects(readFile(output), /ENOENT/);
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
});

test('CLI rejects a FIFO without waiting for a writer', { skip: process.platform === 'win32' }, async () => {
  const folder = await mkdtemp(join(tmpdir(), 'explain-pele-fifo-'));
  try {
    const input = join(folder, 'diagram.mmd');
    await run('mkfifo', [input]);
    await assert.rejects(run(process.execPath, [fileURLToPath(new URL('./render.mjs', import.meta.url)), input, join(folder, 'diagram.svg')], { timeout: 1_000 }), /diagram file/);
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
});
