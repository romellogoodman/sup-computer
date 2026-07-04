// Run a release in the terminal: onnxruntime-node injected into the player's
// backend (ADR-0025), generated text streamed to stdout. Status lines go to
// stderr so `sup shakespeare > out.txt` captures only the text.

import { join } from 'node:path';
import * as ort from 'onnxruntime-node';
import { configureBackend, loadModel, generate } from '@supcomputer/player';
import { pull, makeTokenizer, bundleFor, readManifest } from './artifacts.js';

export async function runModel(model, playerEntry, prompt, flags) {
  await configureBackend({ ort });

  const dir = await pull(model);
  const session = await loadModel(join(dir, bundleFor(model)[0].name));
  const tok = await makeTokenizer(model, dir);

  // Sampling window: player-registry.json for current releases, the export
  // manifest for the rest. Exceeding the real block_size crashes the ONNX
  // RoPE cache, so the guess is the last resort.
  let blockSize = playerEntry?.block_size ?? (await readManifest(model, dir))?.config?.block_size;
  if (!blockSize) {
    process.stderr.write(`  (no block_size in player-registry.json or manifest for ${model.id} — assuming 256)\n`);
    blockSize = 256;
  }

  let stopped = false;
  process.on('SIGINT', () => {
    stopped = true; // let generate() finish the current step, then flush
  });

  process.stdout.write(prompt);
  await generate(session, tok, prompt, {
    maxNewTokens: flags.tokens,
    temp: flags.temp,
    topk: flags.topk,
    blockSize,
    rng: flags.seed === undefined ? undefined : mulberry32(flags.seed),
    onToken: (piece) => process.stdout.write(piece),
    shouldStop: () => stopped,
  });
  process.stdout.write('\n');
}

/** Tiny seedable PRNG — enough for reproducible sampling, not for crypto. */
function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
