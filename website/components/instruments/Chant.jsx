"use client";

// kenosha-kid's instrument: a temperature dial and an endless scroll. The
// six-word chant comes line by line with the DRIFT made visible — every word
// is checked against the model's whole universe ("you never did the kenosha
// kid") and words that have drifted, the near-misses v2's self-drifting
// corpus was built to keep, get the accent. Anchor lines render calm; the
// dream shows up as color. Dreaminess is governed by two knobs, training
// progress and temperature (experiment 03); this dial is the second one.

import { useEffect, useMemo, useRef, useState } from "react";
import TextInstrument from "./TextInstrument";
import { RangeField } from "./Field";

const ANCHOR_WORDS = new Set(["you", "never", "did", "the", "kenosha", "kid"]);
const normalize = (w) => w.toLowerCase().replace(/[^a-z]/g, "");

export function ChantView({ prompt, output, busy }) {
  const text = output || busy ? prompt + output : "";
  const ref = useRef(null);
  // endless scroll: keep the newest line in view while the dream runs
  useEffect(() => {
    const el = ref.current;
    if (el && busy) el.scrollTop = el.scrollHeight;
  }, [text, busy]);
  if (!text) {
    return <div className="chant chant--idle">six words, waiting to be dreamt.</div>;
  }
  const lines = text.split("\n");
  return (
    <div className="chant" aria-live="polite" ref={ref}>
      {lines.map((line, i) => {
        const last = i === lines.length - 1;
        return (
          <div className={line.trim() ? "chant__line" : "chant__gap"} key={i}>
            {line.split(/(\s+)/).map((piece, j) => {
              if (!piece.trim()) return piece;
              const w = normalize(piece);
              const drifted = w && !ANCHOR_WORDS.has(w);
              return drifted ? (
                <span className="chant__drift" key={j}>
                  {piece}
                </span>
              ) : (
                piece
              );
            })}
            {busy && last ? <span className="instrument__cursor">▮</span> : null}
          </div>
        );
      })}
    </div>
  );
}

const DIAL = [
  [0.3, "recites"],
  [0.6, "murmurs"],
  [0.8, "dreams"],
  [1.1, "drifts"],
  [1.4, "babbles"],
];
const dialWord = (t) => DIAL.reduce((w, [at, word]) => (t >= at ? word : w), DIAL[0][1]);

export default function ChantInstrument({ models }) {
  const model = models[0];
  const prompt = model?.demo?.prompt || "You never did the Kenosha Kid";
  const [temp, setTemp] = useState(0.8);
  const defaults = useMemo(() => ({ temp, topk: 0, maxNewTokens: 1200 }), [temp]);
  return (
    <TextInstrument
      model={model}
      prompt={prompt}
      View={ChantView}
      demoLabel="chant"
      runLabel="dream"
      fields={["max"]}
      defaults={defaults}
      placeholder="the chant appears here — the model runs entirely in your browser."
      controls={({ disabled }) => (
        <RangeField
          id="chant-temp"
          label="temperature"
          value={temp}
          onChange={setTemp}
          min={0.2}
          max={1.6}
          step={0.05}
          disabled={disabled}
          format={(t) => `${t.toFixed(2)} · ${dialWord(t)}`}
          ticks={[0.3, 0.6, 0.8, 1.1, 1.4]}
        />
      )}
    />
  );
}
