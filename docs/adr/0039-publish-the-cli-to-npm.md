# ADR 0039: Publish the CLI to npm as `supcpu`

- **Status:** Accepted (amends [ADR-0025](0025-sup-cli-and-injectable-player-backend.md) — decision 4, "not published to npm, deliberately, for now", is reversed; the greeting, the injectable backend, and the suffix-swap consumer stand)
- **Date:** 2026-09-15
- **Deciders:** Romello Goodman (with Claude)

## Context

ADR-0025 kept the `sup` CLI in the clone on purpose: a research project
with no release process, a registry read from the local tree, nothing to
version. That held while the CLI's one job was a terminal greeting for
someone who already had the repo.

Two new front doors changed the job. The hosted API (ADR-0036) runs a model
for anyone with a URL, and the `sup mcp` server (its addendum) gives an
agent the same roster over stdio. Both make "run it without a clone" the
whole point — and the MCP server, in particular, is one config line in a
client: `claude mcp add sup -- npx -y supcpu mcp`. That line only works if
`npx` can find the package. As shipped, the MCP client had to be told the
path to a clone's `cli/bin/sup.js`.

Three things stood between the in-tree package and a tarball that runs
anywhere. The CLI depended on `@supcomputer/player` as `file:../player`, a
symlink into the sibling directory that exists only in a clone.
`registry.json` was read from the repo root by a relative path. And
`onnxruntime-node` — 287 MB on disk, every platform's binaries — loaded at
startup for every command, hosted `sup mcp` included, which never runs a
model in-process. On the npm side the names `supcpu`, `supcomputer`,
`sup-computer`, `@supcomputer/cli`, and `@supcomputer/player` were all
unclaimed, and there was no `supcomputer` org.

## Decision

**1. One package, `supcpu`, two bins.** The package name is the studio's
domain, so `npx supcpu` reads as "run supcpu.com's models"; the bins are
`supcpu` and `sup`, both pointing at `bin/sup.js`, so the docs keep saying
`sup` and `npx` resolves the same program under the package name. Version
`0.1.0`, `license: MIT`, `engines.node >= 20`, `repository` with
`directory: cli`, `homepage: https://www.supcpu.com`, and a `files`
allowlist — `bin`, `src`, `vendor`, `README.md` — so the tarball carries 20
files and 26 kB.

**2. The player ships inside the tarball, sealed at pack time.** No org, no
second package this round. A `prepack` script copies `player/src/` to
`cli/vendor/player/` and `registry.json` to `cli/vendor/registry.json`;
`vendor/` is gitignored and `postpack` removes it. One module,
`cli/src/player.js`, resolves the player once — the vendored copy when it
exists, else `@supcomputer/player` — and every other module imports the
player from there, so the clone and the tarball differ in one line.
`@supcomputer/player` moves from `dependencies` to `devDependencies`: a
clone's `npm install` still links `../player`, and a published manifest
never asks npm to resolve a `file:` path that isn't there. `gpt-tokenizer`,
the player's one runtime dependency, becomes a normal dependency of
`supcpu`. The website's `vercel.json` adds `--include=dev` to its
`npm ci --prefix ../cli` so the hosted API's build keeps the link.

`bundleDependencies` was tried first and rejected on evidence: with the
`file:` symlink, `npm pack` wrote 1,988 entries at
`package/../player/node_modules/…`, the player's whole `node_modules`
included, and nothing at the path Node would resolve.

**3. The registry comes from the site, with a packed snapshot as the floor.**
The site serves `registry.json` at `https://www.supcpu.com/registry.json`:
`sync-content.mjs` copies it into `website/public/` at prebuild, gitignored
like every other synced copy. The CLI resolves the manifest in this order,
first match wins:

1. `$SUP_REGISTRY` — a path or a URL, no cache (a preview deployment, a
   local edit);
2. `registry.json` at the repo root — a clone runs its own tree, exactly as
   before;
3. `~/.cache/supcomputer/registry.json`, when under 24 hours old;
4. the site's copy, fetched with a 5 s timeout and written to that cache;
5. the cache again, however old, when the site did not answer;
6. `vendor/registry.json`, the snapshot sealed at pack time.

`sup list --verbose` names the source on stderr; the normal output is
byte-for-byte what it was. `sup mcp` puts the source in its one stderr
status line.

**4. `onnxruntime-node` loads on the first run, not at startup.** `run.js`
and `generate.js` import it inside the function that needs it. Verified
with a resolve hook on the installed package: hosted `sup mcp` (a
`list_models` and a `generate` against a stub of the API) and `sup list`
resolve no `onnxruntime` specifier; `sup mcp --local` resolves
`onnxruntime-node` on its first `generate`. `sup train` checks for the
repo's `pyproject.toml` and, from an npm install, says it needs the clone.

**5. Versioning and publishing.** The package version is independent of
model releases — a release is a registry entry, and an installed `supcpu`
learns about it from the site within a day (or at once, by deleting
`~/.cache/supcomputer/registry.json`). `sup version` and the MCP handshake
read the version from `package.json`. Publishing is a manual `npm publish
--access public` by the human, from `cli/`, after `npm pack` has been
inspected; nothing in CI publishes. The root `.mcp.json` keeps pointing at
`node cli/bin/sup.js mcp`: a clone should run its own code, and
`cli/README.md` shows both forms and says why.

## Consequences

- A second copy of the player exists at pack time, and only then. Drift
  between `vendor/player` and `player/src` is impossible in the tree
  (postpack deletes it) and bounded in the wild by the package version: a
  player change that matters to the CLI is a `supcpu` bump.
- Registry drift is bounded by the 24-hour cache. An installed `supcpu`
  can show a roster up to a day old, or — with the site down and no cache
  — the roster from the day it was published. The `--verbose` line says
  which; a report of a "missing" model starts there.
- The `npx` cost is `onnxruntime-node`: the tarball is 26 kB, the
  installed tree 359 MB, of which the ORT package is 287 MB (every
  platform's binaries; the Linux prune the site does is not available to
  npm on a laptop). Measured in a clean directory on this connection:
  `npm i supcpu-0.1.0.tgz` took 4.0 s with a warm npm cache and 4.6 s with
  a cold one (153 MB fetched). A first `npx supcpu kenosha-kid` then took
  1.5 s wall including the 3.3 MB artifact download; a warm
  `generate` over MCP `--local` answered in 76 ms. Hosted `sup mcp` pays
  the install and never loads the binding.
- The website depends on `supcpu` (`file:../cli`) instead of
  `@supcomputer/cli`; `lib/inference.js` imports `supcpu/registry`,
  `supcpu/artifacts`, `supcpu/rng`. Its lockfile records the new name and
  the `devDependencies` block, so `npm ci` there needs the regenerated lock
  in the same commit.
- `registry.json` is public at a fixed URL. It already was, in the repo;
  the site's copy is the one the CLI trusts, so a bad registry commit that
  reaches production reaches every installed CLI within a day. The
  integrity check (`tools/check_integrity.py`) runs in CI ahead of that.
- Two names on PATH for one program. `sup` can collide with a user's own
  alias; `supcpu` cannot. If the short name ever has to go, the package
  name is the one the docs would keep.

## Alternatives considered

- **A `@supcomputer` org with two packages** (`@supcomputer/player`,
  `@supcomputer/cli`). Rejected for this round: an org, a second publish,
  and a version coupling between two packages, to save a 15 kB copy of
  five source files. The player's own publish (ADR-0010 anticipated it)
  can come later and the shim in `player.js` is where it would plug in.
- **Bundling ORT** into the tarball, or shipping without it. Rejected:
  the binding is platform-specific and npm's install is the right place
  to pick it; without it, `--local` and every greeting stop working. The
  cost is measured above and accepted.
- **Fetching only `/api/models`** instead of the whole registry. Rejected:
  the API's roster is the newest-per-lineage view; `sup list --all`,
  `sup pull --all`, and `sup run <old-release>` need every release with its
  artifact URLs, which is the registry, and the registry is 21 kB.
- **Rewriting `package.json` at pack time** (strip the `file:` dependency
  in `prepack`, restore in `postpack`). Rejected: a failed pack leaves a
  dirty manifest, and `devDependencies` expresses the same fact with no
  script.
- **`bundleDependencies`.** Rejected on the evidence in decision 2.
- **A conditional `imports` map** (`#player` resolved by a runtime
  condition). Rejected: the condition would have to be passed to Node on
  every invocation, and a bin cannot set its own flags.
