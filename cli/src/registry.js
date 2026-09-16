// Read the in-tree manifest (the CLI runs from the clone, ADR-0025) and
// resolve greeting names — a model id, a series key, or a prefix of one —
// to a runnable release. Bundle resolution and the runnable/lineage rules
// are shared with the website via @supcomputer/player/registry (ADR-0028).

import { readFile } from 'node:fs/promises';
import { resolveBundle, runnable, lineage, latestByLineage as latestOf } from '@supcomputer/player/registry';

export { resolveBundle, runnable, lineage } from '@supcomputer/player/registry';

// One literal `new URL(..., import.meta.url)` so a file tracer (the hosted
// API's bundler, ADR-0036) can see the manifest this module reads.
const REGISTRY = new URL('../../registry.json', import.meta.url); // cli/src/ -> repo root

export async function loadRegistry() {
  return JSON.parse(await readFile(REGISTRY, 'utf8'));
}

/** The newest runnable release of each lineage. */
export function latestByLineage(registry) {
  return latestOf(registry.models);
}

/**
 * The greeting alias: the project name plus any tier suffix the lineage adds
 * beyond its series key — shakespeare, gatsby, kenosha-kid, daydream,
 * daydream-micro, daydream-grand.
 */
export function aliasOf(registry, model) {
  const key = Object.keys(registry.series).find((k) => model.id.startsWith(k));
  if (!key) return lineage(model.id);
  return model.project + lineage(model.id).slice(key.length);
}

/**
 * Resolve what the user greeted. Exact model id wins; otherwise the name must
 * match one series key (exactly or as a prefix — `sup shakespeare` finds
 * `shakespeare-nanogpt`) and resolves to the newest runnable release in it.
 * Where several ids share the newest version (daydream's tiers), the bare
 * series line `<series>-<version>` wins.
 */
export function resolveModel(registry, name) {
  const byId = registry.models.find((m) => m.id === name);
  if (byId) {
    if (!runnable(byId)) throw fail('not-runnable', notRunnable(byId));
    return byId;
  }

  // Greeting aliases — what `sup list` shows (daydream-micro, kenosha-kid, …).
  for (const m of latestByLineage(registry).values()) {
    if (aliasOf(registry, m) === name) return m;
  }

  const keys = Object.keys(registry.series).filter((k) => k === name || k.startsWith(name));
  if (keys.length > 1) {
    throw fail('ambiguous', `"${name}" matches several series: ${keys.join(', ')}`);
  }
  if (keys.length === 1) {
    const key = keys[0];
    const family = registry.models.filter((m) => m.id.startsWith(key) && runnable(m));
    if (!family.length) {
      throw fail('not-runnable', `no runnable release in ${key} yet — its artifacts haven't been published`);
    }
    const newest = Math.max(...family.map((m) => m.version));
    const atNewest = family.filter((m) => m.version === newest);
    return atNewest.find((m) => m.id === `${key}-${newest}`) ?? atNewest[0];
  }

  const near = registry.models.filter((m) => m.id.includes(name)).map((m) => m.id);
  throw fail(
    'unknown',
    near.length
      ? `no model or series named "${name}" — did you mean: ${near.join(', ')}?`
      : `no model or series named "${name}" — try \`sup list\``,
  );
}

/** Every name resolveModel accepts: release ids, greeting aliases, series keys. */
export function greetableNames(registry) {
  const ids = registry.models.filter(runnable).map((m) => m.id);
  const aliases = [...latestByLineage(registry).values()].map((m) => aliasOf(registry, m));
  const series = Object.keys(registry.series).filter((k) =>
    registry.models.some((m) => m.id.startsWith(k) && runnable(m)),
  );
  return { ids, aliases, series };
}

/** A resolution error with a `code` — 'unknown' | 'ambiguous' | 'not-runnable' —
 * so a non-terminal caller (the hosted API) can pick a status without parsing
 * the message. The CLI prints the message and ignores the code. */
function fail(code, message) {
  const err = new Error(message);
  err.code = code;
  return err;
}

function notRunnable(model) {
  if (!resolveBundle(model)) {
    return `${model.id} has no published ONNX artifact yet (registry.json artifacts are null)`;
  }
  return `${model.id} uses the "${model.tokenizer?.type}" tokenizer, which the player doesn't ship`;
}
