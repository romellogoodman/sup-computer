// The inference worker: one model per worker, every session.run off the main
// thread. Instruments never touch ORT directly — they talk to this worker
// through ModelClient (client.js), which is the only place the protocol below
// is spoken.
//
// Why a worker: ORT's WASM backend computes on whatever thread calls it, so
// on the main thread every forward pass froze the page for its duration (the
// old /interfaces jank). Here the page stays responsive and the worker's
// message loop is also the serialization point ORT needs: OrtRun is not
// re-entrant, and overlapping session.run calls corrupt the WASM heap for the
// rest of the page's life (the /interfaces crash, fixed 2026-08-01). Every job
// below chains on ONE promise, so two runs can never interleave.
//
// Protocol (main -> worker), each with a request `id`:
//   load      { url, sidecarUrl, type, blockSize }      -> { vocab | null, webgpu }
//   forward   { ids }                                   -> { logits: Float32Array }
//   encode    { text }                                  -> { ids }
//   decode    { ids }                                   -> { text }
//   generate  { prompt | ids, maxNewTokens, temp, topk, stopAt, topN, seed }
//             streams { type: "token", id, piece, tokId, top } per step,
//             then resolves { text, ids, stopped }
//   stop      { target }   — target is a generate request's id; handled
//                            immediately (not queued), the loop halts at its
//                            next step and resolves with stopped: true.
// Worker -> main: { type: "done", id, result } | { type: "error", id, error }
// | { type: "token", ... }.

import {
  loadModel,
  forward,
  sample,
  CharTokenizer,
  ByteLevelBPETokenizer,
  BPETokenizer,
} from "@supcomputer/player";

let session = null;
let tok = null;
let blockSize = 256;

const stopped = new Set();
let queue = Promise.resolve();
const enqueue = (job) => {
  const next = queue.catch(() => {}).then(job);
  queue = next.catch(() => {}); // an error ends a job, not the chain
  return next;
};

const post = (msg, transfer) => self.postMessage(msg, transfer);

async function makeTokenizer(type, sidecarUrl) {
  if (type === "char") return CharTokenizer.fromUrl(sidecarUrl);
  if (type === "bpe") return ByteLevelBPETokenizer.fromUrl(sidecarUrl);
  if (type === "gpt2-bpe") return BPETokenizer.create();
  return null; // e.g. pona's word tokenizer lives on the main thread
}

/** Softmax at temperature over the logits, then the top-N tokens. */
function topTokens(logits, temp, n) {
  const len = logits.length;
  const t = Math.max(temp, 1e-6);
  let max = -Infinity;
  for (let i = 0; i < len; i++) if (logits[i] > max) max = logits[i];
  const exps = new Float64Array(len);
  let sum = 0;
  for (let i = 0; i < len; i++) {
    exps[i] = Math.exp((logits[i] - max) / t);
    sum += exps[i];
  }
  const idx = Array.from({ length: len }, (_, i) => i).sort((a, b) => logits[b] - logits[a]);
  return idx.slice(0, n).map((i) => ({
    id: i,
    tok: tok ? tok.decode([i]) : String(i),
    prob: exps[i] / sum,
  }));
}

/** Tiny seedable PRNG (mulberry32) — reproducible sampling, nothing more. */
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

async function handle(msg) {
  switch (msg.type) {
    case "load": {
      blockSize = msg.blockSize || 256;
      tok = await makeTokenizer(msg.tokenizer, msg.sidecarUrl);
      session = await loadModel(msg.url);
      let vocab = null;
      if (tok && tok.itos) {
        vocab = [];
        for (const k in tok.itos) vocab[Number(k)] = tok.itos[k];
      }
      return { vocab, webgpu: typeof navigator !== "undefined" && Boolean(navigator.gpu) };
    }
    case "forward": {
      if (!session) throw new Error("no model loaded");
      const logits = await forward(session, msg.ids.slice(-blockSize));
      return { logits: Float32Array.from(logits) };
    }
    case "encode": {
      if (!tok) throw new Error("this model's tokenizer lives on the main thread");
      return { ids: tok.encode(msg.text) };
    }
    case "decode": {
      if (!tok) throw new Error("this model's tokenizer lives on the main thread");
      return { text: tok.decode(msg.ids) };
    }
    case "generate": {
      if (!session) throw new Error("no model loaded");
      const {
        id,
        maxNewTokens = 200,
        temp = 0.8,
        topk = 40,
        stopAt = [],
        topN = 0,
        seed,
      } = msg;
      const ids = msg.ids ? [...msg.ids] : tok.encode(msg.prompt ?? "");
      const rng = seed === undefined ? Math.random : mulberry32(seed);
      const stopSet = new Set(stopAt);
      const genIds = [];
      let emitted = "";
      let wasStopped = false;
      for (let i = 0; i < maxNewTokens; i++) {
        if (stopped.has(id)) {
          wasStopped = true;
          break;
        }
        const logits = await forward(session, ids.slice(-blockSize));
        if (stopped.has(id)) {
          wasStopped = true;
          break;
        }
        const next = sample(logits, { temp, topk, rng });
        const top = topN ? topTokens(logits, temp, topN) : null;
        if (stopSet.has(next)) {
          post({ type: "token", id, piece: "", tokId: next, top, end: true });
          break;
        }
        ids.push(next);
        genIds.push(next);
        let piece = "";
        if (tok) {
          const full = tok.decode(genIds);
          piece = full.slice(emitted.length);
          emitted = full;
        }
        post({ type: "token", id, piece, tokId: next, top });
      }
      stopped.delete(id);
      return { text: emitted, ids: genIds, stopped: wasStopped };
    }
    default:
      throw new Error(`unknown message: ${msg.type}`);
  }
}

self.onmessage = (e) => {
  const msg = e.data;
  if (msg.type === "stop") {
    stopped.add(msg.target);
    return;
  }
  enqueue(() => handle(msg)).then(
    (result) => post({ type: "done", id: msg.id, result }),
    (err) => post({ type: "error", id: msg.id, error: err?.message || String(err) }),
  );
};
