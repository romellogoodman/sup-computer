#!/usr/bin/env node
import { main } from '../src/main.js';

main(process.argv.slice(2)).catch((e) => {
  console.error(`sup: ${e?.message || e}`);
  process.exit(1);
});
