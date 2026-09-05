"use client";

// PLACEHOLDER — glyph's font maker is being built; until it lands the series
// page runs the generic text instrument on the demo prompt ("\na": a
// newline then the letter to draw).

import { useState } from "react";
import TextInstrument from "./TextInstrument";

export default function GlyphMakerInstrument({ models }) {
  const model = models[0];
  const [prompt, setPrompt] = useState(model?.demo?.prompt || "\na");
  return <TextInstrument model={model} prompt={prompt} onPromptChange={setPrompt} />;
}
