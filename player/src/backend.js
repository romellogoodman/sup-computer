// Backend state for the runtime. Web by default: the first loadModel() lazily
// imports the onnxruntime-web WebGPU build (which also carries the WASM
// fallback). A non-browser consumer injects its own ORT implementation instead
// — configureBackend({ ort: onnxruntimeNode }) — so the player itself depends
// on no ORT runtime statically (ADR-0025).

// Must match the onnxruntime-web version in package.json — which is pinned
// EXACT (no caret) because ORT requires the JS and the .wasm artifacts to be
// the same version; bump both together. The .wasm backend artifacts are
// served from a CDN by default so a brand-new consumer folder doesn't have
// to wire its bundler to copy ORT's .wasm files. Override via
// configureBackend({ wasmPaths }) to self-host them.
export const ORT_VERSION = '1.27.0';

let ortModule = null;
let defaultProviders = null;

/**
 * Configure the ORT backend once, idempotently. Subsequent calls return the
 * already-configured module.
 *
 * @param {object} [opts]
 * @param {object}   [opts.ort]                inject an ORT implementation (e.g. onnxruntime-node)
 * @param {string[]} [opts.executionProviders] default providers for injected backends (default ['cpu'])
 * @param {string}   [opts.wasmPaths]          web only: where ORT's .wasm files load from
 * @param {number}   [opts.numThreads]         web only: WASM thread count
 * @returns {Promise<object>} the configured ORT module
 */
export async function configureBackend({ ort, executionProviders, wasmPaths, numThreads } = {}) {
  if (ortModule) return ortModule;

  if (ort) {
    ortModule = ort;
    defaultProviders = executionProviders ?? ['cpu'];
    return ortModule;
  }

  // Browser default. Dynamic so merely importing the player never pulls in
  // onnxruntime-web — in the browser this dovetails with the lazy-ORT loading
  // ADR-0024 wants; in Node it's what makes injection possible at all.
  const web = await import('onnxruntime-web/webgpu');
  web.env.wasm.wasmPaths =
    wasmPaths ?? `https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/`;
  // Multithreaded WASM needs cross-origin isolation (COOP/COEP). If the page
  // isn't isolated, SharedArrayBuffer is unavailable; fall back to 1 thread.
  const isolated =
    typeof globalThis !== 'undefined' && globalThis.crossOriginIsolated === true;
  web.env.wasm.numThreads =
    numThreads ?? (isolated ? Math.min(4, navigator?.hardwareConcurrency ?? 4) : 1);
  ortModule = web;
  defaultProviders = ['webgpu', 'wasm'];
  return ortModule;
}

/** The configured ORT module. Throws before the first configureBackend/loadModel. */
export function getOrt() {
  if (!ortModule) {
    throw new Error('ORT backend not configured — call loadModel() or configureBackend() first');
  }
  return ortModule;
}

/** Execution providers the configured backend defaults to. */
export function getDefaultProviders() {
  return defaultProviders ?? ['webgpu', 'wasm'];
}
