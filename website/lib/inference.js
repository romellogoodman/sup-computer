// The hosted inference API's engine (ADR-0036): the `sup` CLI's name
// resolution and artifact cache, the player's sampling loop, and
// onnxruntime-node injected as the backend — the same three pieces
// `cli/src/run.js` assembles for the terminal, assembled here for a Vercel
// function. Nothing model-specific lives in this file.
//
// Two invariants the function runtime forces:
//   - every ORT session's `run` calls are serialized per model on one promise
//     chain (overlapping runs corrupt the native heap — the same rule as the
//     website's inference worker);
//   - loaded sessions, tokenizers, and the artifact files in /tmp survive
//     between invocations only as long as the instance does, so every entry
//     point tolerates a cold start.

import { readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as ort from "onnxruntime-node";
import { configureBackend, loadModel, generate } from "@supcomputer/player";
import {
  resolveModel,
  latestByLineage,
  aliasOf,
  greetableNames,
  runnable,
} from "supcpu/registry";
import { pull, bundleFor, makeTokenizer } from "supcpu/artifacts";
import { mulberry32 } from "supcpu/rng";

// One literal `new URL(..., import.meta.url)` so the function bundler traces
// the manifest in; the CLI's loadRegistry reads the same file the same way.
export const registry = JSON.parse(readFileSync(new URL("../../registry.json", import.meta.url), "utf8"));

export const LIMITS = {
  tokens: { default: 200, max: 512 },
  temp: { default: 0.8, min: 0.05, max: 2.5 },
  topk: { default: 40, min: 0, max: 1000 },
  prompt: { maxChars: 4000 },
  // Wall clock per request, queue wait included, under the function's
  // maxDuration (300 s). glyph runs ~360 ms/token on the function's vCPU, so
  // 512 tokens of it is ~185 s cold; a request that would overrun stops
  // early and says so (`truncated`) instead of dying as a 504.
  budgetMs: Number(process.env.SUP_API_BUDGET_MS) || 240_000,
};

const CACHE_ROOT = join(tmpdir(), "supcomputer"); // /tmp/supcomputer/<model-id>/ on Vercel

// ---------------------------------------------------------------------------
// Roster and resolution
// ---------------------------------------------------------------------------

const seriesKeyOf = (id) => Object.keys(registry.series).find((k) => id.startsWith(k)) ?? null;

/** What `sup list` shows: the newest runnable release per lineage. */
export function roster() {
  const models = [...latestByLineage(registry).values()].map((m) => ({
    id: m.id,
    alias: aliasOf(registry, m),
    series: seriesKeyOf(m.id),
    version: m.version,
    tagline: m.tagline,
    params: m.params,
    tokenizer: m.tokenizer?.type ?? null,
    block_size: m.block_size ?? null,
    prompt: m.demo?.prompt ?? null,
  }));
  const { series, aliases } = greetableNames(registry);
  return { models, series, aliases };
}

/** Resolve a greeting name; throws with `.code` 'unknown' | 'ambiguous' | 'not-runnable'. */
export function resolve(name) {
  return resolveModel(registry, name);
}

export function validNames() {
  const { ids, aliases, series } = greetableNames(registry);
  return [...new Set([...aliases, ...series, ...ids])];
}

// ---------------------------------------------------------------------------
// Loading — one in-memory entry per model, one promise chain per entry
// ---------------------------------------------------------------------------

const entries = new Map(); // model id -> { session, tokenizer, blockSize, queue }
const loading = new Map(); // model id -> Promise<entry>, so a cold burst loads once

export function loadedIds() {
  return [...entries.keys()];
}

async function load(model) {
  await configureBackend({ ort });
  const dir = await pull(model, { root: CACHE_ROOT, preferInt8: true, quiet: true });
  const graph = bundleFor(model, { preferInt8: true })[0].name;
  const session = await loadModel(join(dir, graph));
  const tokenizer = await makeTokenizer(model, dir);
  // registry.json carries block_size per model (ADR-0028); the ONNX RoPE cache
  // physically ends there, so there is no safe guess past it.
  const blockSize = model.block_size ?? 256;
  return { session, tokenizer, blockSize, queue: Promise.resolve() };
}

export async function ensure(model) {
  if (entries.has(model.id)) return entries.get(model.id);
  if (!loading.has(model.id)) {
    const p = load(model)
      .then((entry) => {
        entries.set(model.id, entry);
        return entry;
      })
      .finally(() => loading.delete(model.id));
    loading.set(model.id, p);
  }
  return loading.get(model.id);
}

/** Run `task` after everything already queued for this model; never overlap. */
function enqueue(entry, task) {
  const run = entry.queue.then(task, task);
  entry.queue = run.then(
    () => undefined,
    () => undefined,
  );
  return run;
}

// ---------------------------------------------------------------------------
// Generation
// ---------------------------------------------------------------------------

/**
 * Parse and clamp a request body into generation options. Throws an Error
 * with `.status = 400` on anything that isn't a number where a number is due.
 */
export function readOptions(body) {
  const bad = (msg) => Object.assign(new Error(msg), { status: 400 });
  const num = (key, fallback) => {
    const v = body[key];
    if (v === undefined || v === null) return fallback;
    const n = typeof v === "number" ? v : Number(v);
    if (!Number.isFinite(n)) throw bad(`${key} must be a number`);
    return n;
  };
  const clamp = (n, lo, hi) => Math.min(hi, Math.max(lo, n));

  if (body.prompt !== undefined && typeof body.prompt !== "string") throw bad("prompt must be a string");
  if (body.prompt && body.prompt.length > LIMITS.prompt.maxChars) {
    throw bad(`prompt is over ${LIMITS.prompt.maxChars} characters`);
  }
  const seed = num("seed", undefined);
  return {
    prompt: body.prompt,
    tokens: Math.round(clamp(num("tokens", LIMITS.tokens.default), 1, LIMITS.tokens.max)),
    temp: clamp(num("temp", LIMITS.temp.default), LIMITS.temp.min, LIMITS.temp.max),
    topk: Math.round(clamp(num("topk", LIMITS.topk.default), LIMITS.topk.min, LIMITS.topk.max)),
    seed: seed === undefined ? undefined : Math.round(seed),
    stream: body.stream === undefined ? true : Boolean(body.stream),
  };
}

/**
 * Generate on a resolved model. `onToken(piece)` streams pieces as they
 * decode; resolves to `{ text, tokens, truncated }` — the continuation
 * (prompt excluded), how many pieces were emitted, and whether the wall-clock
 * budget (from `startedAt`, queue wait included) or `shouldStop` ended the
 * run before `tokens`. Runs on the model's queue so no two ORT runs overlap.
 */
export async function run(model, { prompt, tokens, temp, topk, seed, onToken, shouldStop, startedAt = Date.now() }) {
  const deadline = startedAt + LIMITS.budgetMs;
  const entry = await ensure(model);
  let emitted = 0;
  let overran = false;
  const text = await enqueue(entry, () =>
    generate(entry.session, entry.tokenizer, prompt, {
      maxNewTokens: tokens,
      temp,
      topk,
      blockSize: entry.blockSize,
      rng: seed === undefined ? undefined : mulberry32(seed),
      onToken: async (piece, id) => {
        emitted += 1;
        if (onToken) await onToken(piece, id);
      },
      shouldStop: () => {
        if (shouldStop && shouldStop()) return true;
        if (Date.now() > deadline) {
          overran = true;
          return true;
        }
        return false;
      },
    }),
  );
  return { text, tokens: emitted, truncated: overran };
}

export { runnable };
