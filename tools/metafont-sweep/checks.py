"""
checks.py -- controls for the two measures that came back confounded.

1. Component counts in pixel space are inflated by how far shapes move, not
   by how many knobs moved them. The axes arm has exactly 4 knobs by
   construction, so its own component count is the calibration: if 4 knobs
   need 51 components, component-counting cannot measure knob-count.
2. gzip bytes per glyph is dominated by outline complexity, not corpus
   redundancy. Normalize: compressed bytes as a fraction of raw bytes, at
   matched N, and mean line length alongside.

Also adds the missing baseline for the span measure: how much of the
generative corpus its OWN top-k directions capture, so "64 of Knuth's
directions reach X%" has something to be compared against.
"""
import gzip
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare as C  # noqa: E402
import variety as V  # noqa: E402

KS = [1, 2, 4, 8, 16, 32, 64]


def main():
    letters = sys.argv[1:] or ["a"]
    arms = ["cmss10-axes", "cmss10-indep", "cmr10-indep"]
    out = {}

    for letter in letters:
        rng = np.random.default_rng(C.SEED)
        gen = C.generative(letter, rng)
        par = {a: C.parametric(a, letter) for a in arms}
        par = {a: v for a, v in par.items() if v}
        n = min([len(gen)] + [len(v) for v in par.values()])

        gsel = [gen[i] for i in rng.permutation(len(gen))[:n]]
        Xg = V.rasterize_all(gsel)
        rg, Vtg, mug = V.pca_spectrum(Xg)

        entry = {
            "matched_n": n,
            "self_span": {k: round(float(V.span_fraction(Xg, Vtg, mug, k)), 4)
                          for k in KS},
            "reach": {},
            "line_len": {"generative": round(np.mean([len(x) for x in gsel]), 1)},
            "compression": {},
            "knobs": {"cmss10-axes": 4},
        }
        raw = "\n".join(gsel).encode()
        entry["compression"]["generative"] = round(len(gzip.compress(raw, 9)) / len(raw), 4)

        for arm, lines in par.items():
            sel = [lines[i] for i in rng.permutation(len(lines))[:n]]
            Xp = V.rasterize_all(sel)
            _, Vtp, mup = V.pca_spectrum(Xp)
            entry["reach"][arm] = {k: round(float(V.span_fraction(Xg, Vtp, mup, k)), 4)
                                   for k in KS if k <= Vtp.shape[0]}
            entry["line_len"][arm] = round(np.mean([len(x) for x in sel]), 1)
            raw = "\n".join(sel).encode()
            entry["compression"][arm] = round(len(gzip.compress(raw, 9)) / len(raw), 4)

        out[letter] = entry
        print(f"--- {letter} (n={n} per arm) ---")
        print(f"{'k':>4}  {'own dirs':>9}  " + "  ".join(f"{a:>13}" for a in par))
        for k in KS:
            row = f"{k:>4}  {entry['self_span'][k]*100:>8.1f}%  "
            row += "  ".join(f"{entry['reach'][a].get(k, float('nan'))*100:>12.1f}%" for a in par)
            print(row)
        print("\nmean line length:", entry["line_len"])
        print("gzip / raw      :", entry["compression"])
        print()

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "checks-results.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
