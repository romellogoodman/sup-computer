// After `npm pack`: remove vendor/ so the clone goes back to running the
// linked player and its own registry.json (see prepack.mjs).
import { rm } from 'node:fs/promises';

await rm(new URL('../vendor/', import.meta.url), { recursive: true, force: true });
