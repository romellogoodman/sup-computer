// The player, resolved once (ADR-0039). A clone links the sibling package —
// `@supcomputer/player` is `file:../player` in devDependencies — and the
// published tarball can't, so `npm pack` copies player/src into vendor/player/
// (gitignored, removed at postpack). Whichever exists is the player; every
// module in cli/src imports it from here so the two paths differ in one line.

import { existsSync } from 'node:fs';

const vendored = new URL('../vendor/player/index.js', import.meta.url); // cli/src/ -> cli/vendor/
const player = existsSync(vendored) ? await import(vendored.href) : await import('@supcomputer/player');

export const {
  configureBackend,
  loadModel,
  generate,
  CharTokenizer,
  BPETokenizer,
  ByteLevelBPETokenizer,
  resolveBundle,
  runnable,
  lineage,
  latestByLineage,
} = player;
