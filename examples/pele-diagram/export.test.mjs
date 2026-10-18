import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { readFile, writeFile, mkdtemp, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const run = promisify(execFile);
const files = ['architecture.svg', 'architecture-mobile.svg', 'architecture.png', 'architecture-mobile.png'];
const hashAssets = () => Promise.all(files.map(async (file) => createHash('sha256').update(await readFile(new URL(file, import.meta.url))).digest('hex')));

for (const setting of ['', '/nonexistent/home-hq-font.ttf', 'invalid-file']) {
  test(`preserves assets when the font setting is ${setting || 'empty'}`, async () => {
    const folder = await mkdtemp(join(tmpdir(), 'explain-font-'));
    try {
      let path = setting;
      if (setting === 'invalid-file') {
        path = join(folder, 'invalid.ttf');
        await writeFile(path, 'This is not a font.');
      }
      const before = await hashAssets();
      await assert.rejects(run(process.execPath, [fileURLToPath(new URL('./export.mjs', import.meta.url))], {
        env: { ...process.env, DIAGRAM_FONT_FILES: path }, timeout: 10_000,
      }), /font/i);
      assert.deepEqual(await hashAssets(), before);
    } finally {
      await rm(folder, { recursive: true, force: true });
    }
  });
}
