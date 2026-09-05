"use client";

// shakespeare's instrument: name a speaker, get a scene. The stream is
// typeset as a playbill — speaker tags become small-cap headings, [stage
// directions] go italic and muted, everything else flows as verse in the
// site serif. The parser fails soft: anything it can't classify is a verse
// line, so garbled output still renders (the token view holds the raw truth).

import { useState } from "react";
import TextInstrument from "./TextInstrument";

const SPEAKER_LINE = /^\s{0,4}([A-Z][A-Z .,'’-]{1,28}[.:])\s*$/;
const INLINE_SPEAKER = /^(\s*)([A-Z][A-Z.'’ -]{1,20}\.)\s{2,}(.*)$/;
const STAGE_DIR = /^\s*\[.*\]\s*\.?$/;

const SPEAKERS = ["ROMEO", "JULIET", "HAMLET", "LEAR", "MACBETH", "FOOL", "PROSPERO"];

export function PlaybillView({ prompt, output, busy }) {
  const text = output || busy ? prompt + output : "";
  if (!text) {
    return <div className="playbill playbill--idle">the playbill fills as the model writes.</div>;
  }
  const lines = text.split("\n");
  return (
    <div className="playbill" aria-live="polite">
      {lines.map((line, i) => {
        const last = i === lines.length - 1;
        const cursor = busy && last ? <span className="instrument__cursor">▮</span> : null;
        let m;
        if ((m = line.match(SPEAKER_LINE))) {
          return (
            <div className="playbill__speaker" key={i}>
              {m[1].replace(/[.:]$/, "")}
              {cursor}
            </div>
          );
        }
        if (STAGE_DIR.test(line)) {
          return (
            <div className="playbill__direction" key={i}>
              {line.trim().replace(/^\[_?|_?\]$/g, "")}
              {cursor}
            </div>
          );
        }
        if ((m = line.match(INLINE_SPEAKER))) {
          return (
            <div className="playbill__line" key={i}>
              <span className="playbill__speaker playbill__speaker--inline">{m[2].replace(/\.$/, "")}</span>{" "}
              {m[3]}
              {cursor}
            </div>
          );
        }
        return (
          <div className={line.trim() ? "playbill__line" : "playbill__gap"} key={i}>
            {line}
            {cursor}
          </div>
        );
      })}
    </div>
  );
}

export default function PlaybillInstrument({ models }) {
  const model = models[0];
  // The corpus indents speaker tags by two spaces — the demo prompt in
  // registry.json carries that whitespace on purpose (ADR-0028).
  const [prompt, setPrompt] = useState(model?.demo?.prompt || "  ROMEO:");
  const cue = (name) => setPrompt(`  ${name}:`);
  return (
    <TextInstrument
      model={model}
      prompt={prompt}
      onPromptChange={setPrompt}
      View={PlaybillView}
      demoLabel="playbill"
      runLabel="write"
      placeholder="the scene appears here — the model runs entirely in your browser."
      controls={({ disabled }) => (
        <div className="instrument__chips" role="group" aria-label="cue a speaker">
          <span className="instrument__label">cue</span>
          {SPEAKERS.map((s) => (
            <button
              key={s}
              type="button"
              className={`instrument__chip${prompt.trim() === `${s}:` ? " instrument__chip--on" : ""}`}
              onClick={() => cue(s)}
              disabled={disabled}
            >
              {s}
            </button>
          ))}
        </div>
      )}
    />
  );
}
