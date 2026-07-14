// Download and cache a release's artifact bundle, and build its tokenizer.
//
// The bundle is the ONNX graph plus (for char / corpus-BPE models) a tokenizer
// sidecar whose URL is DERIVED from the ONNX URL by suffix swap — the naming
// convention from ADR-0024, of which this CLI is the second consumer. A missing
// sidecar is reported by its expected name so a broken publish is obvious.

import { mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { CharTokenizer, ByteLevelBPETokenizer, BPETokenizer } from '@supcomputer/player';
import { resolveBundle } from '@supcomputer/player/registry';

export const CACHE_ROOT = process.env.XDG_CACHE_HOME
  ? join(process.env.XDG_CACHE_HOME, 'supcomputer')
  : join(homedir(), '.cache', 'supcomputer');

export function cacheDir(model) {
  return join(CACHE_ROOT, model.id);
}

/** The files a release needs locally: [{ name, url }]. The CLI runs full
 * precision; sidecar names derive from the full-precision name either way
 * (resolveBundle owns that contract). */
export function bundleFor(model) {
  const bundle = resolveBundle(model);
  if (!bundle) throw new Error(`${model.id} has no published ONNX artifact`);
  const files = [{ name: bundle.onnxUrl.split('/').pop(), url: bundle.onnxUrl }];
  if (bundle.sidecarUrl) {
    files.push({ name: bundle.sidecarUrl.split('/').pop(), url: bundle.sidecarUrl, sidecar: true });
  }
  return files; // gpt2-bpe ships its vocab inside gpt-tokenizer — no sidecar
}

/**
 * The export manifest (uploaded beside the ONNX like the tokenizer sidecars)
 * carries the frozen config — a cross-check for registry.json's block_size.
 * Optional: a missing manifest degrades to the caller's fallback, it doesn't
 * fail the pull.
 */
export async function readManifest(model, dir) {
  const url = resolveBundle(model).manifestUrl;
  const name = url.split('/').pop();
  const dest = join(dir, name);
  if (!existsSync(dest)) {
    try {
      const res = await fetch(url);
      if (!res.ok) return null;
      await writeFile(dest, Buffer.from(await res.arrayBuffer()));
    } catch {
      return null;
    }
  }
  const json = JSON.parse(await readFile(dest, 'utf8'));
  return json[model.id] ?? null;
}

/** Ensure the bundle is cached; download whatever is missing. */
export async function pull(model, { force = false } = {}) {
  const dir = cacheDir(model);
  await mkdir(dir, { recursive: true });
  for (const file of bundleFor(model)) {
    const dest = join(dir, file.name);
    if (!force && existsSync(dest)) continue;
    await download(file, dest);
  }
  return dir;
}

async function download(file, dest) {
  const res = await fetch(file.url);
  if (!res.ok) {
    if (file.sidecar) {
      throw new Error(
        `artifact bundle incomplete — expected ${file.name} beside the ONNX ` +
          `(${res.status} at ${file.url}); re-run the publish step so both files sit side by side`,
      );
    }
    throw new Error(`download failed: ${file.url} (${res.status})`);
  }
  const total = Number(res.headers.get('content-length')) || 0;
  const live = process.stderr.isTTY; // only redraw in-place on a real terminal
  const chunks = [];
  let got = 0;
  for await (const chunk of res.body) {
    chunks.push(chunk);
    got += chunk.length;
    if (live && total) {
      process.stderr.write(`\r  ${file.name}  ${mb(got)} / ${mb(total)} MB`);
    }
  }
  const done = `  ${file.name}  ${mb(got)} MB`;
  process.stderr.write(live && total ? `\r${done.padEnd(done.length + 12)}\n` : `${done}\n`);
  await writeFile(dest, Buffer.concat(chunks));
}

const mb = (n) => (n / 1e6).toFixed(1);

export async function removeCached(model) {
  await rm(cacheDir(model), { recursive: true, force: true });
}

/** Build the release's tokenizer from the cached sidecar (or gpt-tokenizer). */
export async function makeTokenizer(model, dir) {
  const type = model.tokenizer?.type;
  if (type === 'gpt2-bpe') return BPETokenizer.create();
  const file = bundleFor(model).find((f) => f.sidecar);
  const json = JSON.parse(await readFile(join(dir, file.name), 'utf8'));
  if (type === 'char') return new CharTokenizer(json.stoi, json.itos);
  if (type === 'bpe') {
    if (json.model?.type !== 'BPE') {
      throw new Error(`unsupported tokenizer model in ${file.name}: ${json.model?.type}`);
    }
    return new ByteLevelBPETokenizer(json.model.vocab, json.model.merges);
  }
  throw new Error(`the player doesn't support the "${type}" tokenizer yet`);
}
