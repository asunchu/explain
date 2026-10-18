import { Worker } from 'node:worker_threads';
import { constants } from 'node:fs';
import { open, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

export const MAX_SOURCE_CHARS = 20_000;
export const MAX_SOURCE_BYTES = 80_000;

export async function renderDiagram(source, { width = 960, now = Date.now(), timeoutMs = 2_000 } = {}) {
  if (typeof source !== 'string') throw new TypeError('Supply diagram source as text.');
  if (!source.trim() || source.length > MAX_SOURCE_CHARS || Buffer.byteLength(source) > MAX_SOURCE_BYTES) {
    throw new Error(`Supply between 1 and ${MAX_SOURCE_CHARS} characters of diagram source.`);
  }
  if (!Number.isInteger(width) || width < 240 || width > 4_096) {
    throw new Error('Set the width between 240 and 4096 pixels.');
  }
  if (!Number.isSafeInteger(now) || !Number.isFinite(new Date(now).valueOf())) {
    throw new Error('Supply a valid timestamp for the current-date marker.');
  }
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 5_000) {
    throw new Error('Set the deadline between 1 and 5000 milliseconds.');
  }

  return new Promise((resolveResult, reject) => {
    const worker = new Worker(new URL('./worker.mjs', import.meta.url), {
      workerData: { source, width, now },
      env: {},
      execArgv: [],
      resourceLimits: { maxOldGenerationSizeMb: 128, maxYoungGenerationSizeMb: 16, stackSizeMb: 4 },
    });
    let finished = false;
    const finish = (error, result) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      // Wait for termination before reporting success or failure to the caller.
      worker.terminate().then(
        () => error ? reject(error) : resolveResult(result),
        () => reject(new Error('The diagram worker could not terminate.')),
      );
    };
    const timer = setTimeout(() => finish(new Error('The diagram exceeded its rendering deadline.')), timeoutMs);
    worker.once('message', (message) => {
      if (!message?.ok) return finish(new Error(message?.message ?? 'The renderer failed.'));
      finish(null, message);
    });
    worker.once('error', () => finish(new Error('The diagram worker failed or exceeded its memory limit.')));
    worker.once('exit', () => finish(new Error('The diagram worker stopped before returning a result.')));
  });
}

async function readBounded(path) {
  // Do not wait for a writer when a local caller supplies a FIFO.
  const file = await open(path, constants.O_RDONLY | (constants.O_NONBLOCK ?? 0));
  try {
    const info = await file.stat();
    if (!info.isFile() || info.size > MAX_SOURCE_BYTES) throw new Error('Supply a diagram file smaller than 80001 bytes.');
    // A bounded read also covers a file that grows after stat().
    const buffer = Buffer.alloc(MAX_SOURCE_BYTES + 1);
    let length = 0;
    while (length < buffer.length) {
      const { bytesRead } = await file.read(buffer, length, buffer.length - length, null);
      if (!bytesRead) break;
      length += bytesRead;
    }
    if (length > MAX_SOURCE_BYTES) throw new Error('The diagram file exceeds 80000 bytes.');
    return new TextDecoder('utf-8', { fatal: true }).decode(buffer.subarray(0, length));
  } finally {
    await file.close();
  }
}

async function main(args) {
  const [input, output, ...flags] = args;
  if (!input || !output || !output.endsWith('.svg') || resolve(input) === resolve(output)) {
    throw new Error('Use: node render.mjs INPUT.mmd OUTPUT.svg [--width PIXELS] [--now ISO_TIME]');
  }
  const options = {};
  const seen = new Set();
  for (let i = 0; i < flags.length; i += 2) {
    const flag = flags[i];
    const value = flags[i + 1];
    if (!value || seen.has(flag) || !['--width', '--now'].includes(flag)) throw new Error('Check the diagram command options.');
    seen.add(flag);
    if (flag === '--width') options.width = Number(value);
    if (flag === '--now') options.now = Date.parse(value);
  }
  const result = await renderDiagram(await readBounded(input), options);
  await writeFile(output, result.svg, { encoding: 'utf8', flag: 'wx' });
  console.log(JSON.stringify({ output, type: result.type, width: result.width, height: result.height, now: result.now }));
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main(process.argv.slice(2)).catch((error) => {
    // JSON quoting keeps source-controlled error text from emitting terminal controls.
    console.error(`Diagram render failed: ${JSON.stringify(error.message)}`);
    process.exitCode = 1;
  });
}
