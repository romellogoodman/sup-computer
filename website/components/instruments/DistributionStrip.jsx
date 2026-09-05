"use client";

// The next-token distribution, rendered under every instrument: the top few
// tokens the model weighed at its latest step, each a chip whose fill is its
// probability. Interpretability as the render — the same strip pona's
// keyboard has shown since release, generalized. `top` comes straight from
// the worker's per-step event ([{ id, tok, prob }], softmax at the run's
// temperature); null before the first step.

const VISIBLE = { " ": "␠", "\n": "↵", "\t": "⇥", "": "∅" };

export function visibleToken(tok) {
  if (tok in VISIBLE) return VISIBLE[tok];
  // BPE pieces carry their leading space; show it so " the" and "the" differ
  return tok.replace(/^ /, "␠").replace(/\n/g, "↵");
}

export default function DistributionStrip({ top, label = "next token", hint }) {
  return (
    <div className="strip" aria-label="the model's next-token distribution">
      <span className="strip__label">{label}</span>
      {top && top.length ? (
        top.map(({ id, tok, prob }) => (
          <span
            className="strip__chip"
            key={id}
            style={{ "--p": `${Math.max(1, Math.round(prob * 100))}%` }}
            title={`${(prob * 100).toFixed(1)}%`}
          >
            <span className="strip__tok">{visibleToken(tok)}</span>
            <span className="strip__prob">{prob >= 0.995 ? "100" : Math.round(prob * 100)}%</span>
          </span>
        ))
      ) : (
        <span className="strip__hint">{hint ?? "the model's top candidates appear here as it writes"}</span>
      )}
    </div>
  );
}
