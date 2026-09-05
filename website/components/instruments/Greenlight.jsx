"use client";

// gatsby's instrument: a topic and the dial. The prompt is the corpus's own
// control line — three repeated [green=N] tags plus the spelled-out intensity
// word, then a topic line (projects/gatsby/generate.py's build_prime; the
// exact shape is a load-bearing contract, so it's mirrored here verbatim).
// In the view, words in the green-light lexicon render in the studio's green
// accent and the pane tints greener as they pile up. Obsession you can watch
// fill the room.

import { useMemo, useState } from "react";
import TextInstrument from "./TextInstrument";
import { RangeField, TextField } from "./Field";

const LEVEL_WORDS = { 1: "faint", 2: "soft", 3: "strong", 4: "heavy", 5: "total" };
export function buildPrime(topic, level) {
  const tag = `[green=${level}]`;
  return `${tag} ${tag} ${tag} obsession=${LEVEL_WORDS[level] ?? "total"}\ntopic: ${topic}\n`;
}

const LEXICON = /^(green|light|greenlight)$/;
const normalize = (w) => w.toLowerCase().replace(/[^a-z]/g, "");

export function GreenlightView({ prompt, output, busy }) {
  // The control line is the prompt; the story is what the model adds.
  const text = output || busy ? output : "";
  if (!text) {
    return <div className="glight glight--idle">across the water, a light.</div>;
  }
  const words = text.split(/(\s+)/);
  let hits = 0;
  const rendered = words.map((piece, j) => {
    if (!piece.trim()) return piece;
    if (LEXICON.test(normalize(piece))) {
      hits += 1;
      return (
        <span className="glight__hit" key={j}>
          {piece}
        </span>
      );
    }
    return piece;
  });
  const wash = Math.min(hits, 24) / 24;
  return (
    <div
      className="glight"
      aria-live="polite"
      style={{ backgroundColor: `color-mix(in srgb, var(--color-accent) ${Math.round(wash * 9)}%, transparent)` }}
    >
      <div className="glight__prime">{prompt.trim()}</div>
      {rendered}
      {busy ? <span className="instrument__cursor">▮</span> : null}
      {hits > 0 && (
        <div className="glight__count">
          {hits} glimpse{hits === 1 ? "" : "s"} of the light
        </div>
      )}
    </div>
  );
}

export default function GreenlightInstrument({ models }) {
  const model = models[0];
  const [level, setLevel] = useState(3);
  const [topic, setTopic] = useState("a boat on the lake");
  const prompt = useMemo(() => buildPrime(topic.trim() || "a boat on the lake", level), [topic, level]);
  const defaults = useMemo(() => ({ temp: 0.8, topk: 40, maxNewTokens: 400 }), []);
  return (
    <TextInstrument
      model={model}
      prompt={prompt}
      View={GreenlightView}
      demoLabel="story"
      runLabel="tell it"
      defaults={defaults}
      placeholder="the story appears here — the model runs entirely in your browser."
      controls={({ disabled }) => (
        <div className="instrument__row">
          <TextField
            id="glight-topic"
            label="topic"
            value={topic}
            onChange={setTopic}
            disabled={disabled}
            placeholder="a boat on the lake"
            maxLength={80}
          />
          <RangeField
            id="glight-level"
            label="green light"
            value={level}
            onChange={setLevel}
            min={1}
            max={5}
            step={1}
            disabled={disabled}
            format={(l) => `${l} · ${LEVEL_WORDS[l]}`}
            ticks={[1, 2, 3, 4, 5]}
          />
        </div>
      )}
    />
  );
}
