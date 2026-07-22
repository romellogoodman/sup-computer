# hf-stage

*Stages a Hugging Face README from a model card (pointer line + absolute links) — part of the publish flow.*

One script, `stage.mjs`. It takes a release's committed model card verbatim,
inserts the standard pointer line after the H1, and rewrites every
repo-relative link and image to an absolute URL (site or GitHub) — the step
that, skipped by hand once, shipped glyph-nanogpt-1's HF card with broken
links. It rides `website/lib/content.js`'s own `resolveLink`/`rewriteAssets`
so link rules have one source of truth, which means it needs the website's
`node_modules`:

```bash
cd website && npm install                             # once
node tools/hf-stage/stage.mjs <model-id> [out-file]   # default: stdout
```
