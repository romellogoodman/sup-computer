// The runtime surface: load a model, run one forward pass (tokens -> logits for
// the last position), sample a token, and an optional autoregressive helper.
//
// The ONNX graph is ONLY the logits oracle. Everything stateful — the loop,
// temperature/top-k, detokenization, rendering — lives here in JS, exactly the
// seam the export enforces.

import { configureBackend, getOrt, getDefaultProviders } from './backend.js';

/**
 * Load an exported .onnx model and return an ORT InferenceSession.
 * In the browser: tries WebGPU, falls back to WASM. With an injected backend
 * (configureBackend({ ort }), ADR-0025): that runtime's providers.
 *
 * @param {string} url  URL/path to the .onnx file (static asset or local file).
 * @param {object} [opts]
 * @param {string[]} [opts.executionProviders]  default: the backend's own
 * @param {string}   [opts.wasmPaths]   override where ORT's .wasm files load from
 */
export async function loadModel(url, opts = {}) {
  const ort = await configureBackend(opts);
  const session = await ort.InferenceSession.create(url, {
    executionProviders: opts.executionProviders ?? getDefaultProviders(),
  });
  return session;
}

/**
 * One forward pass. Takes a sequence of token ids (already windowed to the
 * model's block_size by the caller) and returns the logits for the final
 * position as a Float32Array of length vocab_size.
 *
 * The exported graph slices to the last position, so the output is [1, vocab].
 *
 * @param {ort.InferenceSession} session
 * @param {number[]|Int32Array}  ids
 * @returns {Promise<Float32Array>}
 */
export async function forward(session, ids) {
  const ort = getOrt();
  const len = ids.length;
  // Tokens were exported as int64 (torch.long) -> needs a BigInt64Array.
  const data = new BigInt64Array(len);
  for (let i = 0; i < len; i++) data[i] = BigInt(ids[i]);
  const tokens = new ort.Tensor('int64', data, [1, len]);

  const inputName = session.inputNames[0]; // 'tokens'
  const outputName = session.outputNames[0]; // 'logits'
  const out = await session.run({ [inputName]: tokens });
  return out[outputName].data; // Float32Array, length = vocab_size
}

/**
 * Sample one token id from logits with temperature + optional top-k.
 * Mirrors nanoGPT's sample.py behaviour.
 *
 * @param {Float32Array} logits
 * @param {object} [opts]
 * @param {number} [opts.temp=1.0]
 * @param {number} [opts.topk=0]   0 = no top-k (full distribution)
 * @param {() => number} [opts.rng=Math.random]
 * @returns {number}
 */
export function sample(logits, { temp = 1.0, topk = 0, rng = Math.random } = {}) {
  const n = logits.length;
  const t = Math.max(temp, 1e-6);

  const scaled = new Float64Array(n);
  for (let i = 0; i < n; i++) scaled[i] = logits[i] / t;

  let candidates;
  if (topk && topk < n) {
    const idx = Array.from({ length: n }, (_, i) => i);
    idx.sort((a, b) => scaled[b] - scaled[a]);
    candidates = idx.slice(0, topk);
  } else {
    candidates = Array.from({ length: n }, (_, i) => i);
  }

  let max = -Infinity;
  for (const i of candidates) if (scaled[i] > max) max = scaled[i];

  let sum = 0;
  const probs = candidates.map((i) => {
    const p = Math.exp(scaled[i] - max);
    sum += p;
    return p;
  });

  let r = rng() * sum;
  for (let j = 0; j < candidates.length; j++) {
    r -= probs[j];
    if (r <= 0) return candidates[j];
  }
  return candidates[candidates.length - 1];
}

/**
 * Autoregressive generation. A thin convenience loop over forward + sample +
 * decode. Streams freshly-decoded text to onToken so a UI can render live.
 *
 * Decoding accumulates over all generated ids (then diffs) so multi-byte BPE
 * tokens that span a boundary still decode correctly.
 *
 * @param {ort.InferenceSession} session
 * @param {{encode:(s:string)=>number[], decode:(ids:number[])=>string}} tokenizer
 * @param {string} prompt
 * @param {object} [opts]
 * @param {number} [opts.maxNewTokens=200]
 * @param {number} [opts.temp=0.8]
 * @param {number} [opts.topk=40]
 * @param {number} [opts.blockSize=256]
 * @param {() => number} [opts.rng]  seedable RNG for reproducible sampling
 * @param {(piece:string, id:number)=>void|Promise<void>} [opts.onToken]
 * @param {() => boolean} [opts.shouldStop]  return true to halt early
 * @returns {Promise<string>} the full generated continuation (excludes prompt)
 */
export async function generate(session, tokenizer, prompt, opts = {}) {
  const {
    maxNewTokens = 200,
    temp = 0.8,
    topk = 40,
    blockSize = 256,
    rng,
    onToken,
    shouldStop,
  } = opts;

  const ids = tokenizer.encode(prompt);
  const genIds = [];
  let emitted = '';

  for (let i = 0; i < maxNewTokens; i++) {
    if (shouldStop && shouldStop()) break;
    const window = ids.slice(-blockSize);
    const logits = await forward(session, window);
    const next = sample(logits, { temp, topk, rng });
    ids.push(next);
    genIds.push(next);

    const full = tokenizer.decode(genIds);
    const piece = full.slice(emitted.length);
    emitted = full;
    if (piece && onToken) await onToken(piece, next);
  }

  return emitted;
}
