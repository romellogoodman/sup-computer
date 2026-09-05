// ModelClient — the main-thread handle on one inference worker (worker.js).
// Promise-shaped so instruments read like straight-line code:
//
//   const client = new ModelClient();
//   const { vocab } = await client.load(bundle, model.block_size);
//   const logits = await client.forward(ids);
//   const run = client.generate({ prompt, temp: 0.8, topN: 8 }, (ev) => …);
//   run.stop();               // halts at the next step
//   const { text } = await run.done;
//
// One model per client; an instrument that switches models makes a new client
// (and terminates the old one). All calls on one client are serialized inside
// the worker, so callers never have to think about overlapping runs.

export class ModelClient {
  constructor() {
    this.worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
    this.pending = new Map(); // id -> { resolve, reject, onEvent }
    this.seq = 0;
    this.dead = false;
    this.worker.onmessage = (e) => {
      const msg = e.data;
      const p = this.pending.get(msg.id);
      if (!p) return;
      if (msg.type === "token") {
        p.onEvent?.(msg);
      } else if (msg.type === "done") {
        this.pending.delete(msg.id);
        p.resolve(msg.result);
      } else if (msg.type === "error") {
        this.pending.delete(msg.id);
        p.reject(new Error(msg.error));
      }
    };
    this.worker.onerror = (e) => {
      const err = new Error(e?.message || "inference worker crashed");
      for (const p of this.pending.values()) p.reject(err);
      this.pending.clear();
    };
  }

  request(type, payload = {}, onEvent) {
    if (this.dead) return Promise.reject(new Error("model client terminated"));
    const id = ++this.seq;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject, onEvent });
      this.worker.postMessage({ ...payload, type, id });
    });
  }

  /** bundle: from pickBundle() — { onnxUrl, sidecarUrl, type }. */
  load(bundle, blockSize) {
    return this.request("load", {
      url: bundle.onnxUrl,
      sidecarUrl: bundle.sidecarUrl,
      tokenizer: bundle.type,
      blockSize,
    });
  }

  async forward(ids) {
    const { logits } = await this.request("forward", { ids: Array.from(ids) });
    return logits;
  }

  async encode(text) {
    const { ids } = await this.request("encode", { text });
    return ids;
  }

  async decode(ids) {
    const { text } = await this.request("decode", { ids: Array.from(ids) });
    return text;
  }

  /**
   * Start a generation. opts: { prompt | ids, maxNewTokens, temp, topk,
   * stopAt (token ids that end the run), topN (per-step top tokens for a
   * distribution strip), seed }. onToken receives each step's
   * { piece, tokId, top, end }. Returns { id, done, stop }.
   */
  generate(opts, onToken) {
    const id = ++this.seq;
    const done = new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject, onEvent: onToken });
      this.worker.postMessage({ ...opts, type: "generate", id });
    });
    return { id, done, stop: () => this.stop(id) };
  }

  /** Halt a running generation by its id. Safe to call after it finished. */
  stop(id) {
    if (!this.dead) this.worker.postMessage({ type: "stop", target: id });
  }

  terminate() {
    this.dead = true;
    this.worker.terminate();
    const err = new Error("model client terminated");
    for (const p of this.pending.values()) p.reject(err);
    this.pending.clear();
  }
}
