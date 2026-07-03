/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static studio site: emit plain HTML into out/ (deployable anywhere).
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true }, // we render plain <img>, not next/image
  webpack: (config) => {
    // onnxruntime-web (via @supcomputer/player) defaults to its "bundle" build,
    // whose inlined emscripten loader webpack emits as a raw static/media .mjs
    // that the minifier can't parse ("'import.meta' cannot be used outside of
    // module code"). The package exposes an extern-wasm build behind this
    // custom exports condition; it fetches the .wasm backend from wasmPaths
    // (the player's pinned CDN default) at runtime instead of inlining it.
    config.resolve.conditionNames = ["onnxruntime-web-use-extern-wasm", "..."];
    // ORT also spawns its proxy worker via `new Worker(new URL(import.meta.url))`,
    // which makes webpack emit the module itself as a raw static/media asset that
    // then fails minification. Turn off url/worker parsing for ORT's dist files —
    // worker + wasm loading happen at runtime from the CDN wasmPaths instead.
    config.module.rules.push({
      test: /onnxruntime-web[\\/]dist[\\/].*\.mjs$/,
      parser: { url: false, worker: false },
    });
    return config;
  },
};

export default nextConfig;
