import { parentPort, workerData } from 'node:worker_threads';
import { render } from 'pele';

const { source, width, now } = workerData;

try {
  // Diagram authors cannot enable navigation, remote images, or custom icon markup.
  const result = render(source, {
    links: false,
    images: false,
    linkSchemes: [],
    imageSchemes: [],
    limit: 20_000,
    maxEdges: 500,
    outputLimit: 1_000_000,
    maxWidth: width,
    responsive: true,
    idPrefix: 'explain',
    now,
  });
  if (result.links.length !== 0) throw new Error('The diagram contains active links.');
  if (![result.width, result.height].every((value) => Number.isFinite(value) && value > 0 && value <= 16_384)
      || result.width * result.height > 16_000_000) {
    throw new Error('The diagram dimensions exceed the supported range.');
  }
  parentPort.postMessage({ ok: true, ...result, now });
} catch (error) {
  parentPort.postMessage({ ok: false, message: String(error?.message ?? 'The renderer failed.') });
}
