"use client";

// The instrument slot on a series page. registry.json's `series` map names a
// kind per series; this maps kinds to components and loads only the one the
// page needs (each pulls its own runtime pieces — chess.js for the board,
// opentype.js for the font maker — so the others never ship to that page).
// A series with no kind, or an unknown one, gets the generic text instrument
// on its demo prompt.
//
// `models` is the series' newest release per lineage (one entry, or
// daydream's three tiers); each instrument decides what to do with more than
// one.

import dynamic from "next/dynamic";
import { useState } from "react";
import TextInstrument from "./TextInstrument";

const loading = () => <p className="instrument__loading">loading the instrument…</p>;
const lazy = (load) => dynamic(load, { ssr: false, loading });

const KINDS = {
  playbill: lazy(() => import("./Playbill")),
  chant: lazy(() => import("./Chant")),
  greenlight: lazy(() => import("./Greenlight")),
  board: lazy(() => import("./Board")),
  glyph: lazy(() => import("./GlyphMaker")),
  pona: lazy(() => import("./PonaChat")),
};

function Generic({ models }) {
  const model = models[0];
  const [prompt, setPrompt] = useState(model?.demo?.prompt || "");
  return <TextInstrument model={model} prompt={prompt} onPromptChange={setPrompt} />;
}

export default function Instrument({ kind, series, models }) {
  const Component = KINDS[kind] || Generic;
  return (
    <section className="instrument-frame" id="instrument" aria-label={`${series.name} — the instrument`}>
      <Component series={series} models={models} />
    </section>
  );
}
