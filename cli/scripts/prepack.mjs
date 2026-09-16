// Before `npm pack` / `npm publish` (ADR-0039): seal into vendor/ the two
// things the tarball needs that the tree holds elsewhere — the player's
// source (a clone links ../player; the package can't) and a snapshot of
// registry.json (the roster of last resort when the site is unreachable).
// vendor/ is gitignored; postpack removes it so a clone never runs a stale copy.

import { cp, mkdir, rm, readFile, writeFile } from 'node:fs/promises';

const cli = new URL('../', import.meta.url); // cli/
const vendor = new URL('vendor/', cli);
const player = new URL('../player/', cli);

await rm(vendor, { recursive: true, force: true });
await mkdir(new URL('player/', vendor), { recursive: true });
await cp(new URL('src/', player), new URL('player/', vendor), { recursive: true });
await cp(new URL('../registry.json', cli), new URL('registry.json', vendor));
await cp(new URL('../LICENSE', cli), new URL('LICENSE', cli)); // npm always packs a root LICENSE

const { version: playerVersion } = JSON.parse(await readFile(new URL('package.json', player), 'utf8'));
const { version } = JSON.parse(await readFile(new URL('package.json', cli), 'utf8'));
await writeFile(
  new URL('README.md', vendor),
  `A copy of @supcomputer/player ${playerVersion} (player/src in the repo) and of registry.json, ` +
    `made by \`npm pack\` for supcpu ${version} on ${new Date().toISOString().slice(0, 10)}. ` +
    'The source of both is https://github.com/romellogoodman/sup-computer.\n',
);
console.error(`prepack: vendor/player (@supcomputer/player ${playerVersion}) + vendor/registry.json`);
