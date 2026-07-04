// sup — an ollama for the studio's tiny GPTs.
//
// The invocation is a greeting (ADR-0025): a first argument that isn't a
// reserved subcommand is a model (or series) to say hi to, and with no prompt
// of your own the model answers its player-registry starter prompt in its own
// voice.

import { parseArgs } from 'node:util';
import { loadRegistry, resolveModel, runnable, lineage, latestByLineage, aliasOf } from './registry.js';
import { pull, removeCached, CACHE_ROOT } from './artifacts.js';
import { runModel } from './run.js';

const COMMANDS = new Set(['list', 'pull', 'run', 'rm', 'help']);

const HELP = `sup — run the studio's released models in your terminal

usage:
  sup <model|series> [prompt]   greet a model: sup shakespeare
  sup run <model> [prompt]      the explicit form
  sup list [--all]              what's greetable; --all lists every release by id
  sup pull <model> | --all      download artifacts without running
  sup rm <model> | --all        clear the cache (${CACHE_ROOT})
  sup help                      this text

flags (for run/greeting):
  --temp <t>     sampling temperature      (default 0.8)
  --topk <k>     top-k cutoff, 0 = off     (default 40)
  --tokens <n>   max new tokens            (default 200)
  --seed <n>     seed the sampler for a reproducible generation

Artifacts download once into ${CACHE_ROOT}.
Models: registry.json at the repo root — this CLI runs from the clone.`;

export async function main(argv) {
  const { values: flags, positionals } = parseArgs({
    args: argv,
    options: {
      temp: { type: 'string' },
      topk: { type: 'string' },
      tokens: { type: 'string' },
      seed: { type: 'string' },
      all: { type: 'boolean' },
      force: { type: 'boolean' },
    },
    allowPositionals: true,
  });

  const [first, ...rest] = positionals;
  const registry = await loadRegistry();

  if (!first || first === 'help') return console.log(HELP);
  if (first === 'list') return list(registry, flags);
  if (first === 'pull') return pullCmd(registry, rest[0], flags);
  if (first === 'rm') return rmCmd(registry, rest[0], flags);

  // `sup run <model> [prompt...]` and the greeting `sup <model> [prompt...]`
  const [name, ...promptWords] = first === 'run' ? rest : [first, ...rest];
  if (!name) throw new Error('run what? try `sup list`');

  const model = resolveModel(registry, name);
  const entry = registry.player[model.id];
  const prompt = promptWords.join(' ') || entry?.prompt;
  if (!prompt) {
    throw new Error(`${model.id} has no starter prompt in player-registry.json — pass one: sup run ${model.id} "..."`);
  }

  process.stderr.write(`sup, ${model.id}\n`);
  await runModel(model, entry, prompt, {
    temp: flags.temp !== undefined ? Number(flags.temp) : 0.8,
    topk: flags.topk !== undefined ? Number(flags.topk) : 40,
    tokens: flags.tokens !== undefined ? Number(flags.tokens) : 200,
    seed: flags.seed !== undefined ? Number(flags.seed) : undefined,
  });
}

function list(registry, flags = {}) {
  // One row per lineage, labelled by its greeting alias — daydream's tiers
  // each get a row, superseded versions don't. Series-line rows show the
  // series tagline; tier rows keep their own (the series copy would repeat
  // three times). --all lists every runnable release by full id instead.
  if (flags.all) {
    const rows = registry.models.filter(runnable);
    const width = Math.max(...rows.map((m) => m.id.length));
    for (const m of rows) {
      console.log(`  ${m.id.padEnd(width)}  ${params(m.params)}  ${m.tagline}`);
    }
    return;
  }
  const latest = latestByLineage(registry);
  const rows = [...latest.values()].map((m) => ({ m, alias: aliasOf(registry, m) }));
  const width = Math.max(...rows.map((r) => r.alias.length));
  console.log('runnable:');
  for (const { m, alias } of rows) {
    const tagline = registry.series[lineage(m.id)]?.tagline ?? m.tagline;
    console.log(`  ${alias.padEnd(width)}  ${params(m.params)}  ${tagline}`);
  }
}

const params = (n) => `${(n / 1e6).toFixed(1).padStart(5)}M`;

async function pullCmd(registry, name, flags) {
  const targets = flags.all
    ? registry.models.filter(runnable)
    : [resolveModel(registry, orAsk(name, 'pull'))];
  for (const m of targets) {
    process.stderr.write(`${m.id}\n`);
    await pull(m, { force: flags.force });
  }
}

async function rmCmd(registry, name, flags) {
  const targets = flags.all
    ? registry.models.filter(runnable)
    : [resolveModel(registry, orAsk(name, 'rm'))];
  for (const m of targets) await removeCached(m);
}

function orAsk(name, verb) {
  if (!name) throw new Error(`${verb} what? try \`sup list\` (or --all)`);
  return name;
}
