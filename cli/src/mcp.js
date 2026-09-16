// sup mcp — the studio's models as an MCP server over stdio, so an agent can
// greet a release the way `sup shakespeare` does.
//
// Two backends, one tool surface. The default asks the hosted inference API
// (the website's /api/*, ADR-0036) to run the model; `--local` runs it in this
// process exactly the way `sup run` does (player + onnxruntime-node, artifacts
// cached under ~/.cache/supcomputer). Either way the roster and the name
// resolution are the greeting's: registry.json at the repo root, resolved by
// registry.js, so `kenosha-kid`, `daydream-micro`, and a full release id all
// mean what they mean at the terminal.
//
// stdout is the MCP channel. Nothing here prints to it; status goes to stderr.

import { parseArgs } from 'node:util';
import { readFile } from 'node:fs/promises';
import { McpServer, ResourceTemplate } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { loadRegistry, resolveModel, runnable, latestByLineage, aliasOf } from './registry.js';
import { generateText, MAX_TOKENS } from './generate.js';

export const DEFAULT_API = 'https://www.supcpu.com/api';
const CARD_URI = 'sup://models/{id}/card';
const ROOT = new URL('../../', import.meta.url); // cli/src/ -> repo root

export const MCP_USAGE = `sup mcp [--local] [--api <url>]

  --local        run models in this process (onnxruntime-node) instead of the hosted API
  --api <url>    the hosted API base (default ${DEFAULT_API}, or $SUP_API_URL)`;

const log = (line) => process.stderr.write(`sup mcp: ${line}\n`);

export async function mcp(argv) {
  const { values: flags } = parseArgs({
    args: argv,
    options: { local: { type: 'boolean' }, api: { type: 'string' }, help: { type: 'boolean' } },
  });
  if (flags.help) return process.stderr.write(`${MCP_USAGE}\n`);

  // Belt and braces: anything that reaches console.log would corrupt the
  // protocol stream, so route it to stderr for the life of the server.
  console.log = (...args) => console.error(...args);

  const api = (flags.api ?? process.env.SUP_API_URL ?? DEFAULT_API).replace(/\/$/, '');
  const registry = await loadRegistry();
  const backend = flags.local ? localBackend(registry) : hostedBackend(registry, api);

  const server = new McpServer(
    { name: 'sup', version: '0.0.1' },
    { instructions: INSTRUCTIONS },
  );
  registerTools(server, registry, backend);
  registerResources(server, registry, backend);

  await server.connect(new StdioServerTransport());
  log(`${backend.name} backend, ${registry.models.filter(runnable).length} runnable releases`);
}

const INSTRUCTIONS =
  'sup computer trains small GPTs (0.8M–48M params) on single corpora: Shakespeare, ' +
  'The Great Gatsby, one Pynchon sentence, chess moves, letterforms. They are tiny and ' +
  'they sound like their corpus. `list_models` is the roster; `generate` greets one — ' +
  'with no prompt it answers its starter prompt in its own voice; `model_card` is the ' +
  'release write-up, also attachable as a resource.';

// ---------------------------------------------------------------------------
// Tools

function registerTools(server, registry, backend) {
  server.registerTool(
    'list_models',
    {
      title: 'List the runnable releases',
      description:
        'The greetable roster, what `sup list` shows: the newest runnable release of each ' +
        'lineage with id, series, version, tagline, starter prompt, params, block_size, ' +
        'tokenizer — plus the short names (`shakespeare`, `daydream-micro`, …) that ' +
        '`generate` and `model_card` resolve. Every release, older ones included, is a ' +
        'resource at sup://models/<id>/card.',
      inputSchema: {},
      outputSchema: {
        backend: z.string(),
        models: z.array(z.object({}).passthrough()),
        names: z.record(z.string(), z.string()),
      },
      annotations: { readOnlyHint: true, openWorldHint: backend.name === 'hosted' },
    },
    async () => {
      const roster = { backend: backend.name, models: await backend.roster(), names: names(registry) };
      return { content: [text(JSON.stringify(roster, null, 2))], structuredContent: roster };
    },
  );

  server.registerTool(
    'generate',
    {
      title: 'Generate text from a release',
      description:
        'Greet a model. `model` is a release id (kenosha-kid-nanogpt-2), a short name ' +
        '(kenosha-kid, daydream-grand), or a series prefix; it resolves to the newest ' +
        'runnable release. With no `prompt` the model answers its starter prompt. The ' +
        `continuation is capped at ${MAX_TOKENS} tokens; \`seed\` makes a run reproducible.`,
      inputSchema: {
        model: z.string().describe('release id, short name, or series prefix'),
        prompt: z.string().optional().describe('text to continue; default: the starter prompt'),
        temp: z.number().positive().optional().describe('sampling temperature (default 0.8)'),
        topk: z.number().int().min(0).optional().describe('top-k cutoff, 0 = off (default 40)'),
        tokens: z.number().int().min(1).max(MAX_TOKENS).optional().describe(`max new tokens (default 200, cap ${MAX_TOKENS})`),
        seed: z.number().int().optional().describe('seed the sampler for a reproducible generation'),
      },
      outputSchema: {
        model: z.string(),
        prompt: z.string(),
        text: z.string(),
        tokens: z.number(),
      },
      annotations: { readOnlyHint: true, openWorldHint: backend.name === 'hosted' },
    },
    async ({ model: name, prompt: given, temp = 0.8, topk = 40, tokens = 200, seed }) => {
      const model = resolveModel(registry, name);
      const prompt = given ?? model.demo?.prompt;
      if (!prompt) throw new Error(`${model.id} has no starter prompt — pass one`);
      const out = await backend.generate(model, prompt, { temp, topk, tokens, seed });
      const meta = [`model: ${model.id}`, `${out.tokens} tokens`, `temperature ${temp}`, `top-k ${topk}`]
        .concat(seed === undefined ? [] : [`seed ${seed}`])
        .join(' · ');
      return {
        content: [text(out.text), text(meta)],
        structuredContent: { model: model.id, prompt, text: out.text, tokens: out.tokens },
      };
    },
  );

  server.registerTool(
    'model_card',
    {
      title: "Read a release's model card",
      description:
        'The model card markdown for a release — what it was trained on, how it scored, ' +
        'what it still gets wrong. `model` resolves like `generate`.',
      inputSchema: { model: z.string().describe('release id, short name, or series prefix') },
      annotations: { readOnlyHint: true, openWorldHint: true },
    },
    async ({ model: name }) => {
      const model = resolveModel(registry, name);
      return { content: [text(await backend.card(model))] };
    },
  );
}

const text = (t) => ({ type: 'text', text: t });

/** Short name -> release id: the greeting aliases plus every series key. */
function names(registry) {
  const out = {};
  for (const m of latestByLineage(registry).values()) out[aliasOf(registry, m)] = m.id;
  for (const key of Object.keys(registry.series)) {
    try {
      out[key] = resolveModel(registry, key).id;
    } catch {
      // a series with no runnable release yet doesn't resolve — leave it out
    }
  }
  return out;
}

const seriesOf = (registry, m) => Object.keys(registry.series).find((k) => m.id.startsWith(k)) ?? null;

function rosterRow(registry, m) {
  return {
    id: m.id,
    series: seriesOf(registry, m),
    version: m.version,
    tagline: m.tagline,
    prompt: m.demo?.prompt ?? null,
    params: m.params,
    block_size: m.block_size ?? null,
    tokenizer: m.tokenizer?.type ?? null,
  };
}

// ---------------------------------------------------------------------------
// Resources — one per runnable release: sup://models/<id>/card

function registerResources(server, registry, backend) {
  const runnables = registry.models.filter(runnable);
  const uriFor = (id) => CARD_URI.replace('{id}', id);
  server.registerResource(
    'model-card',
    new ResourceTemplate(CARD_URI, {
      list: () => ({
        resources: runnables.map((m) => ({
          uri: uriFor(m.id),
          name: m.id,
          title: `${m.id} — model card`,
          description: m.tagline,
          mimeType: 'text/markdown',
        })),
      }),
      complete: { id: (value) => runnables.map((m) => m.id).filter((id) => id.startsWith(value)) },
    }),
    {
      title: 'Model card',
      description: "A release's model card: training data, scores, what it still gets wrong.",
      mimeType: 'text/markdown',
    },
    async (uri, { id }) => {
      const model = registry.models.find((m) => m.id === id);
      if (!model) throw new Error(`no release with id "${id}" — the roster is sup://models/<id>/card for each of ${runnables.map((m) => m.id).join(', ')}`);
      return { contents: [{ uri: uri.href, mimeType: 'text/markdown', text: await backend.card(model) }] };
    },
  );
}

// ---------------------------------------------------------------------------
// Backends — same three verbs, roster / generate / card

/**
 * The model card: the in-tree file registry.json points at, or — in a sparse
 * clone without research-docs/ — its markdown twin on the site (ADR-0019,
 * /models/<id>.md). The error names both places tried.
 */
async function readCard(model, siteOrigin) {
  const rel = model.model_card;
  if (rel) {
    try {
      return await readFile(new URL(rel, ROOT), 'utf8');
    } catch (e) {
      if (e.code !== 'ENOENT') throw e;
    }
  }
  const url = `${siteOrigin}/models/${model.id}.md`;
  let res;
  try {
    res = await fetch(url);
  } catch (e) {
    throw new Error(`model card for ${model.id}: ${rel ?? 'no model_card path'} is not in the tree and ${url} did not answer (${e.message})`);
  }
  if (!res.ok) {
    throw new Error(`model card for ${model.id}: ${rel ?? 'no model_card path'} is not in the tree and ${url} answered ${res.status}`);
  }
  return res.text();
}

function localBackend(registry) {
  return {
    name: 'local',
    roster: async () => [...latestByLineage(registry).values()].map((m) => rosterRow(registry, m)),
    generate: async (model, prompt, opts) => {
      const continuation = await generateText(model, prompt, { ...opts, log });
      return { text: prompt + continuation, tokens: Math.min(opts.tokens, MAX_TOKENS) };
    },
    card: (model) => readCard(model, new URL(DEFAULT_API).origin),
  };
}

function hostedBackend(registry, api) {
  const origin = new URL(api).origin;
  const call = async (path, init) => {
    const url = `${api}${path}`;
    let res;
    try {
      res = await fetch(url, init);
    } catch (e) {
      throw new Error(`the hosted API did not answer: ${url} (${e.message}) — try \`sup mcp --local\``);
    }
    const body = await res.text();
    if (!res.ok) {
      let detail = body.slice(0, 200);
      try {
        detail = JSON.parse(body).error ?? detail;
      } catch {
        // not JSON — the trimmed body is the detail
      }
      throw new Error(`${url} answered ${res.status}: ${detail}`);
    }
    return JSON.parse(body);
  };
  return {
    name: 'hosted',
    roster: async () => {
      const json = await call('/models');
      const rows = Array.isArray(json) ? json : (json.models ?? []);
      return rows.map((m) => ({
        id: m.id,
        series: m.series ?? seriesOf(registry, m),
        version: m.version,
        tagline: m.tagline,
        prompt: m.prompt ?? m.demo?.prompt ?? null,
        params: m.params,
        block_size: m.block_size ?? null,
        tokenizer: typeof m.tokenizer === 'string' ? m.tokenizer : (m.tokenizer?.type ?? null),
      }));
    },
    generate: async (model, prompt, { temp, topk, tokens, seed }) => {
      const json = await call('/generate', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ model: model.id, prompt, temp, topk, tokens, seed, stream: false }),
      });
      // The API's `text` is the continuation with the prompt excluded (the
      // player's contract); the tool shows what the terminal shows, prompt first.
      return { text: prompt + (json.text ?? ''), tokens: json.tokens ?? tokens };
    },
    card: (model) => readCard(model, origin),
  };
}
