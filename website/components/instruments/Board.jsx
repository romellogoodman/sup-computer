"use client";

// PLACEHOLDER — daydream's board instrument is being built; until it lands
// the series page runs the generic text instrument on the Regular tier.
// The real component: play against Regular via chess.js, watch-only on
// Micro and Grand, with the candidate-move overlay from a character beam.

import { useState } from "react";
import TextInstrument from "./TextInstrument";

export default function BoardInstrument({ models }) {
  const model = models.find((m) => m.id === "daydream-chess-nanogpt-1") || models[0];
  const [prompt, setPrompt] = useState(model?.demo?.prompt || "");
  return <TextInstrument model={model} prompt={prompt} onPromptChange={setPrompt} />;
}
