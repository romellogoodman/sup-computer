// The package version, read from package.json so `sup version`, the MCP
// server's handshake, and `npm publish` can't disagree.
import { readFileSync } from 'node:fs';

export const VERSION = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8')).version;
