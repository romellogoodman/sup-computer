// Copy content from the monorepo into website/ at build time.
//
// content/ is the source the pages read (gitignored); the source of truth lives
// next to the experiments (research-docs/) and in registry.json. Report chart
// assets are copied into public/ so they can be served. Run automatically via the
// prebuild/predev npm hooks, or by hand with `npm run sync-content`. Never edit
// the copies — they're blown away and regenerated every run.

import { cp, rm, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..", "..");
const contentDir = resolve(here, "..", "content");
const publicAssets = resolve(here, "..", "public", "research-assets");

// [ repo-root path, destination under content/ ]
const DIRS = [["research-docs", "research-docs"]];
const FILES = [["registry.json", "registry.json"]];
// chart assets served as static files (image paths are rewritten to /research-assets/)
const ASSET_DIRS = [["research-docs/reports/assets", publicAssets]];

await rm(contentDir, { recursive: true, force: true });
await mkdir(contentDir, { recursive: true });

for (const [src, out] of DIRS) {
  await cp(resolve(repoRoot, src), resolve(contentDir, out), { recursive: true });
  console.log(`synced ${src}/ -> content/${out}/`);
}
for (const [src, out] of FILES) {
  const from = resolve(repoRoot, src);
  if (existsSync(from)) {
    await cp(from, resolve(contentDir, out));
    console.log(`synced ${src} -> content/${out}`);
  }
}
await rm(publicAssets, { recursive: true, force: true });
for (const [src, dst] of ASSET_DIRS) {
  const from = resolve(repoRoot, src);
  if (existsSync(from)) {
    await cp(from, dst, { recursive: true });
    console.log(`synced ${src}/ -> public/research-assets/`);
  }
}
