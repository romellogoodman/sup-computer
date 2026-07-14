// Registry helpers — the single owner of ADR-0024's artifact-bundle naming
// convention and of which tokenizer types the player ships. Exported as the
// `@supcomputer/player/registry` subpath so consumers (the website page, the
// sup CLI) can import it statically without touching the runtime's lazy ORT
// / gpt-tokenizer graph. See ADR-0028.

export const SUPPORTED_TOKENIZERS = ['char', 'bpe', 'gpt2-bpe'];

export function tokenizerSupported(model) {
  return SUPPORTED_TOKENIZERS.includes(model.tokenizer?.type);
}

/**
 * Resolve a registry.json model entry to its runnable file set, or null if no
 * ONNX artifact is published. `preferInt8` picks the quantized graph when one
 * exists (smaller download — the browser's choice); the default is full
 * precision (the CLI's choice). Sidecar and manifest names ALWAYS derive from
 * the full-precision name by suffix swap, whichever graph runs — that is the
 * publish contract (ADR-0024).
 */
export function resolveBundle(model, { preferInt8 = false } = {}) {
  const { onnx, onnx_int8: int8 } = model.artifacts ?? {};
  const onnxUrl = (preferInt8 ? int8 || onnx : onnx || int8) || null;
  if (!onnxUrl) return null;
  const base = (onnx || onnxUrl).replace(/\.int8(?=\.onnx$)/, '');
  const type = model.tokenizer?.type;
  const sidecarUrl =
    type === 'char'
      ? base.replace(/\.onnx$/, '.vocab.json')
      : type === 'bpe'
        ? base.replace(/\.onnx$/, '.tokenizer.json')
        : null; // gpt2-bpe ships its vocab inside gpt-tokenizer — no sidecar
  return { onnxUrl, sidecarUrl, manifestUrl: base.replace(/\.onnx$/, '.manifest.json'), type };
}

export function runnable(model) {
  return Boolean(resolveBundle(model)) && tokenizerSupported(model);
}

/** A lineage is an id minus its version: daydream's tiers are separate lineages. */
export const lineage = (id) => id.replace(/-\d+$/, '');

/** The newest runnable release of each lineage — the demo roster, derived. */
export function latestByLineage(models) {
  const latest = new Map();
  for (const m of models.filter(runnable)) {
    const key = lineage(m.id);
    if (!latest.has(key) || m.version > latest.get(key).version) latest.set(key, m);
  }
  return latest;
}
