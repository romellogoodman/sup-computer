// Find the manifest and resolve greeting names — a model id, a series key, or
// a prefix of one — to a runnable release. Bundle resolution and the
// runnable/lineage rules are shared with the website via the player (ADR-0028).
//
// Where the manifest comes from (ADR-0039), first match wins:
//   1. $SUP_REGISTRY — a path or a URL, no cache
//   2. registry.json at the repo root — a clone runs its own tree (ADR-0025)
//   3. ~/.cache/supcomputer/registry.json, when under a day old
//   4. https://www.supcpu.com/registry.json, then cached
//   5. the cache again, however old, when the site did not answer
//   6. vendor/registry.json — the snapshot `npm pack` sealed into the tarball

import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { resolveBundle, runnable, lineage, latestByLineage as latestOf } from './player.js';
import { CACHE_ROOT } from './artifacts.js';

export { resolveBundle, runnable, lineage } from './player.js';

export const SITE_ORIGIN = 'https://www.supcpu.com';
export const REGISTRY_URL = `${SITE_ORIGIN}/registry.json`;

// One literal `new URL(..., import.meta.url)` per file so a file tracer (the
// hosted API's bundler, ADR-0036) can see the manifest this module reads.
const IN_TREE = new URL('../../registry.json', import.meta.url); // cli/src/ -> repo root
const SNAPSHOT = new URL('../vendor/registry.json', import.meta.url); // cli/src/ -> cli/vendor/
const CACHE_FILE = join(CACHE_ROOT, 'registry.json');
const MAX_AGE_MS = 24 * 60 * 60 * 1000;
const FETCH_TIMEOUT_MS = 5000;

/** The manifest, from the first source that has it. `log` (optional) is told which. */
export async function loadRegistry({ log } = {}) {
  const { registry, source } = await resolveRegistry();
  log?.(`registry: ${source}`);
  return registry;
}

/** The manifest and a one-line account of where it came from. */
export async function resolveRegistry() {
  const env = process.env.SUP_REGISTRY;
  if (env) {
    if (/^https?:\/\//.test(env)) return { registry: await fetchRegistry(env), source: `${env} ($SUP_REGISTRY)` };
    return { registry: parse(await readFile(env, 'utf8'), env), source: `${env} ($SUP_REGISTRY)` };
  }

  if (existsSync(IN_TREE)) {
    return { registry: parse(await readFile(IN_TREE, 'utf8'), IN_TREE), source: `${fileURLToPath(IN_TREE)} (the clone)` };
  }

  const age = await ageOf(CACHE_FILE);
  if (age !== null && age < MAX_AGE_MS) {
    return { registry: parse(await readFile(CACHE_FILE, 'utf8'), CACHE_FILE), source: `${CACHE_FILE} (cached ${hours(age)} ago)` };
  }

  let failure;
  try {
    const registry = await fetchRegistry(REGISTRY_URL);
    try {
      await mkdir(CACHE_ROOT, { recursive: true });
      await writeFile(CACHE_FILE, JSON.stringify(registry, null, 2));
    } catch {
      // a read-only home still runs; it just fetches every time
    }
    return { registry, source: REGISTRY_URL };
  } catch (e) {
    failure = e.message;
  }

  if (age !== null) {
    return {
      registry: parse(await readFile(CACHE_FILE, 'utf8'), CACHE_FILE),
      source: `${CACHE_FILE} (cached ${hours(age)} ago; ${REGISTRY_URL} did not answer: ${failure})`,
    };
  }
  if (existsSync(SNAPSHOT)) {
    return {
      registry: parse(await readFile(SNAPSHOT, 'utf8'), SNAPSHOT),
      source: `the snapshot packed with this version (${REGISTRY_URL} did not answer: ${failure})`,
    };
  }
  throw new Error(`no registry: ${REGISTRY_URL} did not answer (${failure}) and nothing is cached or packed`);
}

async function fetchRegistry(url) {
  let res;
  try {
    res = await fetch(url, { signal: AbortSignal.timeout(FETCH_TIMEOUT_MS) });
  } catch (e) {
    throw new Error(e.name === 'TimeoutError' ? `no answer in ${FETCH_TIMEOUT_MS / 1000} s` : e.message);
  }
  if (!res.ok) throw new Error(`answered ${res.status}`);
  return parse(await res.text(), url);
}

function parse(text, where) {
  let json;
  try {
    json = JSON.parse(text);
  } catch (e) {
    throw new Error(`${where} is not JSON: ${e.message}`);
  }
  if (!Array.isArray(json.models) || typeof json.series !== 'object') {
    throw new Error(`${where} is not a registry (no models list or series map)`);
  }
  return json;
}

async function ageOf(path) {
  try {
    return Date.now() - (await stat(path)).mtimeMs;
  } catch {
    return null;
  }
}

const hours = (ms) => {
  const h = ms / 3600000;
  return h < 1 ? `${Math.round(ms / 60000)} min` : `${h.toFixed(h < 10 ? 1 : 0)} h`;
};

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
