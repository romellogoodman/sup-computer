#!/usr/bin/env node
// Stage a Hugging Face model-repo README from a release's committed model
// card. The checked-in version of the throwaway rewriter each publish used
// to re-derive from memory — glyph-nanogpt-1 shipped with broken relative
// links because that step got skipped; this script exists so it can't be.
//
// Rides website/lib/content.js's own resolveLink/rewriteAssets (one source
// of truth for link rules), so it needs the website's node_modules:
//
//   cd website && npm install          # once
//   node tools/hf-stage/stage.mjs <model-id> [out-file]   # default: stdout
//
// Output: the card verbatim, plus the standard pointer line after the H1,
// with every repo-relative link/image rewritten absolute (site or GitHub).

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const { resolveLink, rewriteAssets, SITE_URL, GITHUB } = await import(
  pathToFileURL(path.join(ROOT, "website", "lib", "content.js"))
);

const [id, outFile] = process.argv.slice(2);
if (!id) {
  console.error("usage: node tools/hf-stage/stage.mjs <model-id> [out-file]");
  process.exit(1);
}

const registry = JSON.parse(fs.readFileSync(path.join(ROOT, "registry.json"), "utf8"));
const model = registry.models.find((m) => m.id === id);
if (!model) {
  console.error(`no "${id}" in registry.json`);
  process.exit(1);
}

const cardPath = path.join(ROOT, model.model_card);
let body = fs.readFileSync(cardPath, "utf8");

// The standard pointer line (format set by the 2026-07-02 releases).
const frozen = model.frozen_code.replace(/\/$/, "");
const pointer =
  `> A [sup computer](${SITE_URL}) release — a small language model studio. ` +
  `[Model page](${SITE_URL}/models/${model.id}/) · [monorepo](${GITHUB}) ` +
  `(frozen code: [\`${model.frozen_code}\`](${GITHUB}/tree/main/${frozen}), tag \`${model.git_tag}\`) · ` +
  `runs in your browser at [www.supcpu.com/interfaces](${SITE_URL}/interfaces/).`;

// Asset paths -> /research-assets/, then markdown links -> site/GitHub URLs,
// then absolutize the root-relative results for HF.
body = rewriteAssets(body);
body = body.replace(/(\]\()([^)\s]+)((?:\s+"[^"]*")?\))/g, (full, open, target, close) => {
  const next = resolveLink(target, "research-docs/model-cards");
  return next ? `${open}${next}${close}` : full;
});
body = body.replace(/(\]\(|src="|srcset=")\//g, `$1${SITE_URL}/`);

// Insert (or refresh) the pointer line after the H1.
const lines = body.split("\n");
const h1 = lines.findIndex((l) => /^#\s+/.test(l));
if (h1 === -1) {
  console.error(`${model.model_card} has no H1 to anchor the pointer line`);
  process.exit(1);
}
if (lines[h1 + 2]?.startsWith("> A [sup computer](")) {
  lines[h1 + 2] = pointer; // already staged once — refresh in place
} else {
  lines.splice(h1 + 1, 0, "", pointer);
}
body = lines.join("\n");

// Safety: nothing repo-relative may survive into the HF copy.
const leftovers = [...body.matchAll(/\]\((?!https?:|mailto:|tel:|#)([^)\s]+)/g)].map((m) => m[1]);
if (leftovers.length) {
  console.error(`unresolved relative links: ${leftovers.join(", ")}`);
  process.exit(1);
}

if (outFile) {
  fs.mkdirSync(path.dirname(outFile), { recursive: true });
  fs.writeFileSync(outFile, body);
  console.error(`staged ${model.model_card} -> ${outFile}`);
} else {
  process.stdout.write(body);
}
