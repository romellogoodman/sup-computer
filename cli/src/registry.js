// Read the in-tree manifest (the CLI runs from the clone, ADR-0025) and
// resolve greeting names — a model id, a series key, or a prefix of one —
// to a runnable release. Bundle resolution and the runnable/lineage rules
// are shared with the website via @supcomputer/player/registry (ADR-0028).

import { readFile } from 'node:fs/promises';
import { resolveBundle, runnable, lineage, latestByLineage as latestOf } from '@supcomputer/player/registry';

export { resolveBundle, runnable, lineage } from '@supcomputer/player/registry';

const ROOT = new URL('../../', import.meta.url); // cli/src/ -> repo root

export async function loadRegistry() {
  return JSON.parse(await readFile(new URL('registry.json', ROOT), 'utf8'));
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
    if (!runnable(byId)) throw new Error(notRunnable(byId));
    return byId;
  }

  // Greeting aliases — what `sup list` shows (daydream-micro, kenosha-kid, …).
  for (const m of latestByLineage(registry).values()) {
    if (aliasOf(registry, m) === name) return m;
  }

  const keys = Object.keys(registry.series).filter((k) => k === name || k.startsWith(name));
  if (keys.length > 1) {
    throw new Error(`"${name}" matches several series: ${keys.join(', ')}`);
  }
  if (keys.length === 1) {
    const key = keys[0];
    const family = registry.models.filter((m) => m.id.startsWith(key) && runnable(m));
    if (!family.length) {
      throw new Error(`no runnable release in ${key} yet — its artifacts haven't been published`);
    }
    const newest = Math.max(...family.map((m) => m.version));
    const atNewest = family.filter((m) => m.version === newest);
    return atNewest.find((m) => m.id === `${key}-${newest}`) ?? atNewest[0];
  }

  const near = registry.models.filter((m) => m.id.includes(name)).map((m) => m.id);
  throw new Error(
    near.length
      ? `no model or series named "${name}" — did you mean: ${near.join(', ')}?`
      : `no model or series named "${name}" — try \`sup list\``,
  );
}

function notRunnable(model) {
  if (!resolveBundle(model)) {
    return `${model.id} has no published ONNX artifact yet (registry.json artifacts are null)`;
  }
  return `${model.id} uses the "${model.tokenizer?.type}" tokenizer, which the player doesn't ship`;
}
