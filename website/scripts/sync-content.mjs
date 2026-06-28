// Copy cross-project markdown into website/content/ at build time.
//
// content/ is gitignored: the source of truth lives next to the experiments
// (research-docs/, written by Claude). The website is a pure consumer — it never
// edits these files, it pulls fresh copies on every build. Run automatically via
// the prebuild/predev npm hooks, or by hand with `npm run sync-content`.

import { cp, rm, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..", "..");
const dest = resolve(here, "..", "content");

// [ path relative to repo root, destination subdir under website/content/ ]
const SOURCES = [["research-docs", "research-docs"]];

await rm(dest, { recursive: true, force: true });
await mkdir(dest, { recursive: true });

for (const [src, out] of SOURCES) {
  await cp(resolve(repoRoot, src), resolve(dest, out), { recursive: true });
  console.log(`synced ${src}/ -> website/content/${out}/`);
}
