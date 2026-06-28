// Small backend for the Shakespeare GPT web UI.
// Exposes POST /generate, which shells out to the trained nanoGPT model
// (models/shakespeare-nanogpt-1) and returns the generated text. Zero
// dependencies — just Node's built-in http + child_process.

import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { writeFile, unlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PORT = process.env.PORT || 3000;
// Repo root, derived from this file's location (web-ui/ is one level down), so the
// app isn't pinned to any one machine's checkout path.
const MODEL_DIR = join(dirname(fileURLToPath(import.meta.url)), "..");
const PYTHON = join(MODEL_DIR, ".venv/bin/python");

// The char-level model only knows these 65 characters. Anything else would
// crash its encoder, so we strip unknown characters from the user's prompt.
const VOCAB = new Set("\n !$&',-.3:;?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz");

function sanitize(text) {
  const cleaned = [...String(text)].filter((c) => VOCAB.has(c)).join("");
  return cleaned.length ? cleaned : "\n"; // model needs at least one token
}

// sample.py prints some log lines, then the generated text, then a "-----" rule.
// Pull out just the generated text.
function parseOutput(stdout) {
  const lines = stdout.split("\n");
  let i = lines.findIndex((l) => l.startsWith("Loading meta") || l.startsWith("No meta.pkl"));
  i = i === -1 ? 0 : i + 1;
  const out = [];
  for (; i < lines.length; i++) {
    if (/^-{5,}$/.test(lines[i].trim())) break;
    out.push(lines[i]);
  }
  return out.join("\n").trim();
}

async function runModel({ start, maxNewTokens = 300, temperature = 0.8 }) {
  // Pass the prompt via a temp file (--start=FILE:...) so arbitrary user text is
  // never interpolated into a command line.
  const promptPath = join(tmpdir(), `wy-prompt-${process.pid}-${Date.now()}.txt`);
  await writeFile(promptPath, sanitize(start), "utf8");
  const args = [
    "models/shakespeare-nanogpt-1/sample.py", // self-contained v1; reads its own ckpt.pt
    "--device=mps",
    "--num_samples=1", // single sample, no batching
    `--max_new_tokens=${Math.min(Math.max(Number(maxNewTokens) || 300, 1), 1000)}`,
    `--temperature=${Number(temperature) || 0.8}`,
    `--start=FILE:${promptPath}`,
  ];
  try {
    return await new Promise((resolve, reject) => {
      const proc = spawn(PYTHON, args, { cwd: MODEL_DIR });
      let stdout = "";
      let stderr = "";
      proc.stdout.on("data", (d) => (stdout += d));
      proc.stderr.on("data", (d) => (stderr += d));
      proc.on("error", reject);
      proc.on("close", (code) => {
        if (code !== 0) return reject(new Error(stderr.trim() || `model exited with code ${code}`));
        resolve(parseOutput(stdout));
      });
    });
  } finally {
    unlink(promptPath).catch(() => {});
  }
}

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

const server = createServer((req, res) => {
  if (req.method === "OPTIONS") {
    res.writeHead(204, CORS);
    return res.end();
  }

  if (req.method === "POST" && req.url === "/generate") {
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", async () => {
      try {
        const { start = "", maxNewTokens, temperature } = JSON.parse(body || "{}");
        const output = await runModel({ start, maxNewTokens, temperature });
        res.writeHead(200, { ...CORS, "Content-Type": "application/json" });
        res.end(JSON.stringify({ output }));
      } catch (err) {
        res.writeHead(500, { ...CORS, "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: String(err.message || err) }));
      }
    });
    return;
  }

  res.writeHead(200, { ...CORS, "Content-Type": "text/plain" });
  res.end("Shakespeare GPT server. POST /generate { start, maxNewTokens?, temperature? }");
});

server.listen(PORT, () => {
  console.log(`Shakespeare GPT model server listening on http://localhost:${PORT}`);
});
