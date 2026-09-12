"use client";

// pona's instrument: talk with the word-arm model through its own vocabulary.
// The transcript alternates your turns with the model's (it speaks as "ilo"),
// framed exactly as projects/pona/talk.py frames them; the composer offers free
// typing AND the word keyboard (the vocab IS the keyboard); the suggestion
// strip shows the model's top next-word probabilities for the current
// composition, straight from the worker's forward() logits — and, while ilo
// answers, the distribution it sampled each word from.
//
// Inference runs in the instrument worker (lib/instrument): every
// session.run is serialized there, so the crash invariant from the old
// /interfaces page (never overlap two ORT runs) holds by construction, and
// the page never janks. The word tokenizer is the one piece that stays on
// the main thread — the player doesn't ship it — so this component encodes
// and decodes itself via lib/pona.js and sends token ids across.

import { useEffect, useMemo, useRef, useState } from "react";
import { useModel } from "../../lib/instrument/useModel";
import { pickBundle } from "../../lib/instrument/bundle";
import { BackendLine } from "./Field";
import {
  UNK,
  NAME,
  NAME_DISPLAY,
  NO_SPACE_BEFORE,
  NO_SPACE_AFTER,
  MAX_REPLY_TOKENS,
  REPLY_TEMP,
  encode,
  detok,
  display,
  frameContext,
  keyboardSections,
  PLACEHOLDER_SECTIONS,
  pickPonaModel,
} from "../../lib/pona";

const SUGGEST_COUNT = 5;
const SUGGEST_DEBOUNCE_MS = 250;

// The vocab sidecar name follows the publish contract (ADR-0024): a suffix
// swap on the full-precision <id>.onnx name — pickBundle's manifestUrl already
// carries that base (localized for dev, too).
function vocabUrlOf(model) {
  const b = pickBundle(model);
  return b ? b.manifestUrl.replace(/\.manifest\.json$/, ".vocab.json") : null;
}

// Softmax over the full distribution, then the top-k tokens by probability.
// <unk> is skipped — it isn't a word anyone can tap.
function topSuggestions(logits, itos, k) {
  const n = logits.length;
  let max = -Infinity;
  for (let i = 0; i < n; i++) if (logits[i] > max) max = logits[i];
  const exps = new Float64Array(n);
  let sum = 0;
  for (let i = 0; i < n; i++) {
    exps[i] = Math.exp(logits[i] - max);
    sum += exps[i];
  }
  const idx = Array.from({ length: n }, (_, i) => i).sort((a, b) => logits[b] - logits[a]);
  const out = [];
  for (const i of idx) {
    if (itos[i] === UNK) continue;
    out.push({ tok: itos[i], prob: exps[i] / sum });
    if (out.length === k) break;
  }
  return out;
}

export default function PonaChat({ models }) {
  const model = useMemo(() => pickPonaModel(models), [models]);
  const m = useModel(model);
  const runnable = model && m.state !== "unpublished";
  const blockSize = model?.block_size || 256;

  const [vocab, setVocab] = useState(null); // { stoi, itos[] } from the released sidecar
  const [vocabError, setVocabError] = useState(null);
  const [turns, setTurns] = useState([]); // { who: "sina" | "ilo", text }
  const [composition, setComposition] = useState("");
  const [pending, setPending] = useState(null); // the ilo reply streaming in
  const [error, setError] = useState(null);
  const [woken, setWoken] = useState(false); // first touch triggers the ONNX download
  const [suggestions, setSuggestions] = useState(null);

  const suggestSeqRef = useRef(0); // only the newest suggestion query may land
  const pendingRef = useRef(null); // mirror of `pending` for stop() to commit
  const runRef = useRef(null);

  const busy = m.state === "loading" || m.generating;
  const canSend = runnable && Boolean(vocab) && !busy && composition.trim().length > 0;

  // The vocab sidecar is a small JSON — fetch it eagerly (no ORT involved) so
  // the real keyboard renders on load even before the model wakes.
  useEffect(() => {
    const url = vocabUrlOf(model);
    if (!url) return undefined;
    let alive = true;
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`vocab fetch failed (${r.status})`);
        return r.json();
      })
      .then(({ stoi, itos }) => {
        if (!alive) return;
        const arr = [];
        for (const k in itos) arr[Number(k)] = itos[k];
        setVocab({ stoi, itos: arr });
      })
      .catch((e) => alive && setVocabError(e?.message || String(e)));
    return () => {
      alive = false;
    };
  }, [model]);

  // The suggestion strip: after every composition/transcript change, one
  // debounced forward() for the framed context. The worker queues it behind
  // any reply in flight; superseded queries drop themselves via suggestSeqRef.
  useEffect(() => {
    if (!runnable || !vocab || !woken || m.generating) return undefined;
    const seq = ++suggestSeqRef.current;
    const timer = setTimeout(() => {
      const history = turns.map((t) => t.text);
      const ids = encode(frameContext(history, composition), vocab.stoi);
      m.forward(ids.slice(-blockSize))
        .then((logits) => {
          if (seq !== suggestSeqRef.current) return;
          setSuggestions(topSuggestions(logits, vocab.itos, SUGGEST_COUNT));
        })
        .catch(() => {}); // suggestions fail silently; send() surfaces real errors
    }, SUGGEST_DEBOUNCE_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [composition, turns, woken, runnable, vocab, m.generating]);

  const wake = () => {
    if (!woken) setWoken(true);
    if (runnable && m.state === "cold") m.ensure().catch(() => {});
  };

  // Append one vocabulary token to the composition with pona_tok's spacing.
  const appendToken = (tok) => {
    wake();
    setComposition((c) => {
      if (NO_SPACE_BEFORE.has(tok)) return c.replace(/\s+$/, "") + tok;
      const last = c[c.length - 1];
      const needSpace = c.length > 0 && !/\s$/.test(c) && !NO_SPACE_AFTER.has(last);
      return needSpace ? `${c} ${tok}` : c + tok;
    });
  };

  const send = async () => {
    const text = composition.replace(/\s+/g, " ").trim();
    if (!text || !runnable || !vocab || busy) return;
    const history = [...turns.map((t) => t.text), text];
    setTurns((t) => [...t, { who: "sina", text }]);
    setComposition("");
    setSuggestions(null);
    setError(null);
    setPending("");
    pendingRef.current = "";
    // The chat contract (talk.py / chat_eval.py): frame the last 8 turns,
    // sample at temp 0.8 over the full distribution, stop at the newline
    // token or 36 tokens, detok for display.
    const ids = encode(frameContext(history), vocab.stoi);
    const nl = vocab.stoi["\n"];
    const words = [];
    const handle = m.generate(
      {
        ids: ids.slice(-blockSize),
        maxNewTokens: MAX_REPLY_TOKENS,
        temp: REPLY_TEMP,
        topk: 0,
        stopAt: [nl],
        topN: SUGGEST_COUNT + 1,
      },
      (ev) => {
        if (ev.top) {
          setSuggestions(
            ev.top
              .filter((t) => vocab.itos[t.id] !== UNK)
              .slice(0, SUGGEST_COUNT)
              .map((t) => ({ tok: vocab.itos[t.id], prob: t.prob })),
          );
        }
        if (ev.end) return;
        words.push(vocab.itos[ev.tokId]);
        const sofar = display(detok(words));
        pendingRef.current = sofar;
        setPending(sofar);
      },
    );
    runRef.current = handle;
    try {
      const { stopped } = await handle.done;
      if (stopped) return; // stop() already committed the partial
      const reply = display(detok(words)) || "…";
      pendingRef.current = null;
      setPending(null);
      setTurns((t) => [...t, { who: "ilo", text: reply }]);
    } catch (e) {
      pendingRef.current = null;
      setPending(null);
      setError(e?.message || String(e));
    }
  };

  // Whatever the model had said so far stays in the transcript as its
  // (cut-off) turn.
  const stop = () => {
    runRef.current?.stop();
    const partial = pendingRef.current;
    pendingRef.current = null;
    setPending(null);
    if (partial) setTurns((t) => [...t, { who: "ilo", text: partial }]);
  };

  const tapSuggestion = (tok) => {
    if (tok === "\n") {
      if (canSend) send();
      return;
    }
    appendToken(tok === NAME ? NAME_DISPLAY : tok);
  };

  const sections = useMemo(
    () => (vocab ? keyboardSections(vocab.itos) : PLACEHOLDER_SECTIONS),
    [vocab],
  );
  const keyCount =
    sections.common.length + sections.punct.length + sections.names.length + sections.rare.length;

  const keyButton = (tok, extra = "") => (
    <button key={tok} type="button" className={`pona__key${extra}`} onClick={() => appendToken(tok)}>
      {tok}
    </button>
  );

  const suggestHint = !woken
    ? "tap a key or start typing — the model wakes on first touch"
    : m.state === "loading"
      ? "loading the model…"
      : m.state === "failed"
        ? "suggestions unavailable"
        : "…";

  return (
    <div className="pona">
      {!runnable && (
        <p className="pona__notice">ilo pona li lape. (pona is still training — check back soon)</p>
      )}
      {runnable && vocabError && (
        <p className="pona__notice">the keyboard&rsquo;s vocabulary failed to load: {vocabError}</p>
      )}
      {m.state === "failed" && <p className="pona__notice">the model failed to load: {m.error}</p>}

      <div className="pona__transcript" aria-live="polite">
        {turns.length === 0 && pending == null && (
          <p className="pona__hint">ilo li kute.</p>
        )}
        {turns.length === 0 && pending == null && (
          <p className="pona__hint">
            type below or tap the keys; the model answers word by word, as{" "}
            <strong>ilo</strong>.
          </p>
        )}
        {turns.map((t, i) => (
          <p key={i} className={`pona__turn pona__turn--${t.who}`}>
            <span className="pona__who">{t.who}</span>
            {t.text}
          </p>
        ))}
        {pending != null && (
          <p className="pona__turn pona__turn--ilo">
            <span className="pona__who">ilo</span>
            {pending}
            <span className="pona__cursor">▮</span>
          </p>
        )}
      </div>

      {runnable && (
        <div className="pona__suggest" aria-label="the model's top next-word suggestions">
          <span className="pona__suggest-label">next word</span>
          {suggestions ? (
            suggestions.map(({ tok, prob }) => (
              <button
                key={tok === "\n" ? "\\n" : tok}
                type="button"
                className="pona__sugg"
                onClick={() => tapSuggestion(tok)}
                title={tok === "\n" ? "end the turn (send)" : undefined}
                disabled={m.generating}
              >
                {tok === "\n" ? "↵" : tok === NAME ? NAME_DISPLAY : tok}
                <span className="pona__sugg-prob">{Math.round(prob * 100)}%</span>
              </button>
            ))
          ) : (
            <span className="pona__suggest-hint">{suggestHint}</span>
          )}
        </div>
      )}

      {error && <p className="pona__error">error: {error}</p>}

      <form
        className="pona__composer"
        onSubmit={(e) => {
          e.preventDefault();
          if (canSend) send();
        }}
      >
        <label className="sr-only" htmlFor="pona-input">
          your turn, in Toki Pona
        </label>
        <input
          id="pona-input"
          className="pona__input"
          type="text"
          autoComplete="off"
          autoCapitalize="none"
          spellCheck={false}
          placeholder="toki…"
          value={composition}
          onChange={(e) => {
            wake();
            setComposition(e.target.value);
          }}
          onFocus={wake}
        />
        {busy ? (
          <button type="button" className="pona__send" onClick={stop}>
            stop
          </button>
        ) : (
          <button type="submit" className="pona__send" disabled={!canSend}>
            send
          </button>
        )}
      </form>

      <div className="pona__keyboard" role="group" aria-label="the word keyboard">
        <div className="pona__keys">{sections.common.map((tok) => keyButton(tok))}</div>
        <div className="pona__keys pona__keys--punct">
          {sections.punct.map((tok) => keyButton(tok, " pona__key--punct"))}
        </div>
        {(sections.names.length > 0 || sections.rare.length > 0) && (
          <details className="pona__rare">
            <summary className="pona__rare-summary">
              nimi ante — names &amp; rare words ({sections.names.length + sections.rare.length})
            </summary>
            <div className="pona__keys">
              {[...sections.names, ...sections.rare].map((tok) => keyButton(tok))}
            </div>
          </details>
        )}
        <p className="pona__caption">
          {vocab
            ? `${keyCount} keys — the model's entire vocabulary, one key per token.`
            : "a sample of the keyboard — the released model's full vocabulary becomes the keys."}
        </p>
      </div>
      <BackendLine state={m.state} backend={m.backend} model={model} />
    </div>
  );
}
