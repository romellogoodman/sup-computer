// In-process generation that returns a string instead of streaming to stdout —
// what `sup mcp --local` runs, the same way `sup run` does it (player +
// onnxruntime-node, artifacts via artifacts.js), minus the terminal.
//
// Sessions load once per release and stay warm. Generation is serialized
// through one promise queue: two overlapping `session.run` calls on one ORT
// session corrupt the WASM heap (the /interfaces crash), and a client is free
// to call `generate` twice at once, so the queue is the invariant, not a
// courtesy.

import { join } from 'node:path';
import * as ort from 'onnxruntime-node';
import { configureBackend, loadModel, generate } from '@supcomputer/player';
import { pull, makeTokenizer, bundleFor, readManifest } from './artifacts.js';

export const MAX_TOKENS = 512;

const loaded = new Map(); // model id -> { session, tok, blockSize }
let queue = Promise.resolve();

/** Load (or reuse) a release's session + tokenizer. Status goes to stderr. */
export async function loadRelease(model, { log = () => {} } = {}) {
  if (loaded.has(model.id)) return loaded.get(model.id);
  await configureBackend({ ort });
  const dir = await pull(model);
  const session = await loadModel(join(dir, bundleFor(model)[0].name));
  const tok = await makeTokenizer(model, dir);
  let blockSize = model.block_size ?? (await readManifest(model, dir))?.config?.block_size;
  if (!blockSize) {
    log(`no block_size in registry.json or manifest for ${model.id} — assuming 256`);
    blockSize = 256;
  }
  const entry = { session, tok, blockSize };
  loaded.set(model.id, entry);
  return entry;
}

/**
 * Generate a continuation for `prompt` and return it (prompt excluded).
 * Calls are queued so at most one forward pass runs at a time.
 */
export function generateText(model, prompt, { temp = 0.8, topk = 40, tokens = 200, seed, log } = {}) {
  const job = async () => {
    const { session, tok, blockSize } = await loadRelease(model, { log });
    return generate(session, tok, prompt, {
      maxNewTokens: Math.min(tokens, MAX_TOKENS),
      temp,
      topk,
      blockSize,
      rng: seed === undefined ? undefined : mulberry32(seed),
    });
  };
  const result = queue.then(job, job);
  queue = result.catch(() => {}); // a failed job must not poison the queue
  return result;
}

/** Tiny seedable PRNG — enough for reproducible sampling, not for crypto. */
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
