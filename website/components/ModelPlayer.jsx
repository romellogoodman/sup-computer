"use client";

// The /model-player demo: pick a release on the left, run it in the browser on
// the right. Inference is @supcomputer/player (onnxruntime-web) — imported
// lazily on first Generate so the ORT bundle never loads for readers who don't
// press the button. The ONNX + vocab URLs come from registry.json artifacts;
// while those are null (no weights published yet) the panel renders a
// "weights not yet published" state instead of a runnable demo.

import { useMemo, useRef, useState } from "react";

const DEFAULTS = { temp: 0.8, topk: 40, maxNewTokens: 200 };

// Which artifact to run: prefer the int8 quantization (smaller download),
// fall back to full-precision ONNX.
function onnxUrl(model) {
  return model.artifacts?.onnx_int8 || model.artifacts?.onnx || null;
}

// Tokenizer files sit next to the .onnx with derived names — <model>.vocab.json
// (char, from export.py) or <model>.tokenizer.json (corpus-trained BPE, the
// committed HF tokenizer.json) — rather than being their own registry fields.
async function makeTokenizer(model, runtime, url) {
  const type = model.tokenizer?.type;
  if (type === "char") return runtime.CharTokenizer.fromUrl(url.replace(/\.onnx$/, ".vocab.json"));
  if (type === "bpe") return runtime.ByteLevelBPETokenizer.fromUrl(url.replace(/\.onnx$/, ".tokenizer.json"));
  if (type === "gpt2-bpe") return runtime.BPETokenizer.create();
  throw new Error(`the player doesn't support the "${type}" tokenizer yet`);
}

function tokenizerSupported(model) {
  return ["char", "bpe", "gpt2-bpe"].includes(model.tokenizer?.type);
}

export default function ModelPlayer({ models, series, player }) {
  // player-registry.json decides which releases the list shows (the latest per
  // series) and in what order; registry.json supplies the model facts. It also
  // carries the demo settings — starter prompt and the release's block_size.
  const latest = useMemo(
    () => Object.keys(player).map((id) => models.find((m) => m.id === id)).filter(Boolean),
    [models, player],
  );

  const [selectedId, setSelectedId] = useState(latest[0]?.id);
  const selected = models.find((m) => m.id === selectedId);

  const [prompt, setPrompt] = useState(player[selectedId]?.prompt || "");
  const [temp, setTemp] = useState(DEFAULTS.temp);
  const [topk, setTopk] = useState(DEFAULTS.topk);
  const [maxNewTokens, setMaxNewTokens] = useState(DEFAULTS.maxNewTokens);

  const [output, setOutput] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | generating | error
  const [error, setError] = useState(null);

  const cache = useRef({}); // id -> { session, tok }, kept across model switches
  const stopRef = useRef(false);

  const url = selected ? onnxUrl(selected) : null;
  const runnable = Boolean(url) && tokenizerSupported(selected);
  const busy = status === "loading" || status === "generating";

  const select = (m) => {
    if (busy) stopRef.current = true;
    setSelectedId(m.id);
    setPrompt(player[m.id]?.prompt || "");
    setOutput("");
    setError(null);
    setStatus("idle");
  };

  const run = async () => {
    if (!runnable || busy) return;
    setOutput("");
    setError(null);
    setStatus("loading");
    stopRef.current = false;
    try {
      // NB: named `runtime`, not `player` — that would shadow the registry prop
      const runtime = await import("@supcomputer/player");
      let entry = cache.current[selected.id];
      if (!entry) {
        const session = await runtime.loadModel(url);
        const tok = await makeTokenizer(selected, runtime, url);
        entry = cache.current[selected.id] = { session, tok };
      }
      setStatus("generating");
      await runtime.generate(entry.session, entry.tok, prompt, {
        maxNewTokens,
        temp,
        topk,
        blockSize: player[selected.id]?.block_size || 256,
        onToken: (piece) => setOutput((s) => s + piece),
        shouldStop: () => stopRef.current,
      });
      setStatus("idle");
    } catch (e) {
      setError(e?.message || String(e));
      setStatus("error");
    }
  };

  const stop = () => {
    stopRef.current = true;
  };

  return (
    <div className="player">
      <div className="player__bar">
        <label className="sr-only" htmlFor="player-select">
          model
        </label>
        <select
          id="player-select"
          className="player__select"
          value={selectedId}
          onChange={(e) => {
            const m = latest.find((x) => x.id === e.target.value);
            if (m) select(m);
          }}
        >
          {latest.map((m) => (
            <option key={m.id} value={m.id}>
              {m.id}
            </option>
          ))}
        </select>
      </div>

      {selected && (
        <div className="player__head">
          <h2 className="player__model-title">
            <a href={`/models/${selected.id}/`}>{selected.id}</a>
          </h2>
          {(() => {
            // The series tagline from registry.json's `series` map — the same
            // copy the homepage model list shows. Matched by prefix so tier ids
            // (daydream's -micro/-grand) resolve to their series too.
            const key = Object.keys(series).find((k) => selected.id.startsWith(k));
            const tagline = series[key]?.tagline;
            return tagline && <p className="player__tagline">{tagline}</p>;
          })()}
        </div>
      )}

      {selected && (
        <section className="player__body" aria-label={`${selected.id} demo`}>
          {!url && (
            <p className="player__notice">
              weights not yet published for this release. The demo lights up the moment
              they land; everything else is already wired.
            </p>
          )}
          {url && !tokenizerSupported(selected) && (
            <p className="player__notice">
              the player doesn't ship a "{selected.tokenizer.type}" tokenizer yet, so this
              release can't run in the browser.
            </p>
          )}

          <label className="player__label" htmlFor="player-prompt">
            prompt
          </label>
          <textarea
            id="player-prompt"
            className="player__prompt"
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={!runnable || busy}
          />

          <div className="player__controls">
            <label className="player__control">
              <span className="player__label">temp</span>
              <input
                type="number"
                min="0.1"
                max="2"
                step="0.1"
                value={temp}
                onChange={(e) => setTemp(Number(e.target.value))}
                disabled={!runnable || busy}
              />
            </label>
            <label className="player__control">
              <span className="player__label">top-k</span>
              <input
                type="number"
                min="0"
                max="200"
                step="1"
                value={topk}
                onChange={(e) => setTopk(Number(e.target.value))}
                disabled={!runnable || busy}
              />
            </label>
            <label className="player__control">
              <span className="player__label">max tokens</span>
              <input
                type="number"
                min="1"
                max="1000"
                step="1"
                value={maxNewTokens}
                onChange={(e) => setMaxNewTokens(Number(e.target.value))}
                disabled={!runnable || busy}
              />
            </label>
            {status === "generating" ? (
              <button type="button" className="player__button" onClick={stop}>
                stop
              </button>
            ) : (
              <button
                type="button"
                className="player__button"
                onClick={run}
                disabled={!runnable || busy}
              >
                {status === "loading" ? "loading model…" : "generate"}
              </button>
            )}
          </div>

          {error && <p className="player__error">error: {error}</p>}

          <pre className="player__output" aria-live="polite">
            {prompt && (output || busy) ? <span className="player__output-prompt">{prompt}</span> : null}
            {output ||
              (busy
                ? ""
                : runnable
                  ? "output appears here — the model runs entirely in your browser."
                  : "no runnable artifact for this release yet.")}
            {status === "generating" && <span className="player__cursor">▮</span>}
          </pre>
        </section>
      )}
    </div>
  );
}
