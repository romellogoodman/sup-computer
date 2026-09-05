// sup train — train a small GPT on your own text file. The work is Python:
// core's `sup-train` entry point (nanogpt_core.train_corpus) runs prepare →
// train → sample → export → card stub. This spawns it in the repo's uv venv
// with stdio inherited, so the trainer's log streams straight through, and
// keeps your working directory, so `./corpus.txt` and `--out` mean what they
// would in your shell. Flags pass through untouched; `sup train --help` is
// the Python side's help.

import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = fileURLToPath(new URL('../../', import.meta.url)); // cli/src/ -> repo root

export const TRAIN_USAGE =
  'sup train <corpus.txt> [--out DIR] [--size tiny|small|medium] [--iters N] ' +
  '[--tokenizer char|bpe] [--name NAME] [--device DEV] [--no-export]';

export function train(args) {
  if (args.length === 0) throw new Error(`train what? usage: ${TRAIN_USAGE}`);
  return new Promise((resolve, reject) => {
    const child = spawn('uv', ['run', '--project', REPO_ROOT, 'sup-train', ...args], { stdio: 'inherit' });
    child.on('error', (err) => {
      reject(
        err.code === 'ENOENT'
          ? new Error(
              '`sup train` needs uv on your PATH — it runs the Python trainer in the repo venv. ' +
                'Install it from https://docs.astral.sh/uv/ then `uv sync --extra export` in the repo root.',
            )
          : err,
      );
    });
    child.on('exit', (code, signal) => {
      // exit with the trainer's code; a signal (Ctrl-C) is the shell's 128 + 2
      process.exitCode = code ?? (signal === 'SIGINT' ? 130 : 1);
      resolve();
    });
  });
}
