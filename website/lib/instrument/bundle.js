// Which artifact an instrument runs, and where it loads from.
//
// The naming contract (sidecar and manifest derive from the full-precision
// .onnx name) belongs to the player — resolveBundle is its single owner
// (ADR-0028). This module adds the two things only the website knows:
//
//   1. the int8 policy. Dynamic int8 graphs run on the WASM execution
//      provider only (MatMulInteger has no WebGPU kernel, so a WebGPU session
//      would silently fall back per node and get *slower*). So: int8 when the
//      browser has no WebGPU, full precision when it does. The download is
//      bigger on WebGPU machines, but it's cached for a week (the R2
//      Cache-Control) and the compute is an order of magnitude faster.
//   2. a local override for development. Set NEXT_PUBLIC_ARTIFACTS_BASE
//      (e.g. "/artifacts") and every artifact URL is rewritten to that base
//      + the file's name; website/public/artifacts/ is gitignored and can
//      hold symlinks into projects/*/dist/. The R2 bucket's CORS only admits
//      port 3000, so any other dev port needs this.

import { resolveBundle, tokenizerSupported } from "@supcomputer/player/registry";

const LOCAL_BASE = (process.env.NEXT_PUBLIC_ARTIFACTS_BASE || "").replace(/\/$/, "");

export function localize(url) {
  if (!LOCAL_BASE || !url) return url;
  return `${LOCAL_BASE}/${url.split("/").pop()}`;
}

/** Does this browser expose WebGPU at all? (ORT may still fall back to WASM.) */
export function hasWebGPU() {
  return typeof navigator !== "undefined" && Boolean(navigator.gpu);
}

/**
 * The bundle an instrument should load for a registry model entry, or null
 * while the release has no published artifacts. `type` is the tokenizer type
 * from the registry ("char" | "bpe" | "gpt2-bpe" | anything else — the worker
 * only builds a tokenizer for the three the player ships).
 */
export function pickBundle(model) {
  if (!model) return null;
  const webgpu = hasWebGPU();
  const b = resolveBundle(model, { preferInt8: !webgpu });
  if (!b) return null;
  return {
    onnxUrl: localize(b.onnxUrl),
    sidecarUrl: localize(b.sidecarUrl),
    manifestUrl: localize(b.manifestUrl),
    type: b.type,
    int8: /\.int8\.onnx$/.test(b.onnxUrl),
    webgpu,
  };
}

/** Runnable in the generic sense: artifacts published + a player tokenizer. */
export function isRunnable(model) {
  return Boolean(resolveBundle(model)) && tokenizerSupported(model);
}
