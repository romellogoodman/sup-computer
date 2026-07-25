"""
scale.py -- does sampling a parameter space harder buy you anything?

Same four knobs, 498 settings vs 2,972. If the corpus's information is capped
by the parameterization rather than by how many draws you take, the extra
2,474 fonts should move neither the reach into real design space nor the
marginal cost per glyph.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare as C  # noqa: E402
import saturate as S  # noqa: E402
import variety as V  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BIG = os.path.join(HERE, "mf_big", "cmss10-axes")
KS = [4, 8, 16, 32, 64, 128]


def main():
    letters = sys.argv[1:] or ["a"]
    out = {}
    for letter in letters:
        rng = np.random.default_rng(C.SEED)
        gen = C.generative(letter, rng)
        small = C.parametric("cmss10-axes", letter)
        big = [line for _, _, line in V.load_corpus(os.path.join(BIG, f"{letter}.txt"), letter)]

        Xg = V.rasterize_all(gen)
        entry = {"n": {"generative": len(gen), "sweep_498": len(small), "sweep_2972": len(big)},
                 "reach": {}, "marginal_over_raw": {}, "dims95": {}}

        for name, lines in (("sweep_498", small), ("sweep_2972", big)):
            X = V.rasterize_all(lines)
            ratios, Vt, mu = V.pca_spectrum(X)
            entry["dims95"][name] = V.dims_for(ratios)[0.95]
            entry["reach"][name] = {k: round(float(V.span_fraction(Xg, Vt, mu, k)), 4)
                                    for k in KS if k <= Vt.shape[0]}
            _, _, mn = S.curve(lines, np.random.default_rng(C.SEED))
            entry["marginal_over_raw"][name] = mn

        rg, Vtg, mug = V.pca_spectrum(Xg)
        entry["dims95"]["generative"] = V.dims_for(rg)[0.95]
        entry["reach"]["generative_own"] = {k: round(float(V.span_fraction(Xg, Vtg, mug, k)), 4)
                                            for k in KS if k <= Vtg.shape[0]}
        _, _, mn = S.curve(gen, np.random.default_rng(C.SEED))
        entry["marginal_over_raw"]["generative"] = mn

        out[letter] = entry
        print(f"--- {letter} ---   n: {entry['n']}")
        print(f"{'k':>5} " + "".join(f"{c:>16}" for c in ("sweep 498", "sweep 2972", "own dirs")))
        for k in KS:
            r = [entry["reach"]["sweep_498"].get(k), entry["reach"]["sweep_2972"].get(k),
                 entry["reach"]["generative_own"].get(k)]
            print(f"{k:>5} " + "".join(f"{(v*100 if v is not None else float('nan')):>15.1f}%" for v in r))
        print("dims@95%:", entry["dims95"])
        print("marginal bytes / raw bytes:", entry["marginal_over_raw"])
        print()

    with open(os.path.join(HERE, "scale-results.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
