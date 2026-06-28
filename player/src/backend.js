// Backend init for onnxruntime-web. Loads the WebGPU build (which also carries
// the WASM fallback). Configured once, lazily, on first loadModel().

import * as ort from 'onnxruntime-web/webgpu';

// Must match the onnxruntime-web version in package.json. The .wasm backend
// artifacts are served from a CDN by default so a brand-new consumer folder
// doesn't have to wire its bundler to copy ORT's .wasm files. Override via
// configureBackend({ wasmPaths }) to self-host them.
export const ORT_VERSION = '1.27.0';

let configured = false;

export function configureBackend({ wasmPaths, numThreads } = {}) {
  if (configured) return;
  ort.env.wasm.wasmPaths =
    wasmPaths ?? `https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/`;
  // Multithreaded WASM needs cross-origin isolation (COOP/COEP). If the page
  // isn't isolated, SharedArrayBuffer is unavailable; fall back to 1 thread.
  const isolated =
    typeof globalThis !== 'undefined' && globalThis.crossOriginIsolated === true;
  ort.env.wasm.numThreads =
    numThreads ?? (isolated ? Math.min(4, navigator?.hardwareConcurrency ?? 4) : 1);
  configured = true;
}

export { ort };
