"""
control.py -- the honest baseline for the reach measure.

Scoring a corpus against directions fitted on itself is in-sample and
optimistic; the parameter sweep never gets that advantage. So: hold out half
the families, fit every arm's directions on an equal number of samples from
the other half (or from the sweep), and score all of them on the same
held-out glyphs.

Ceiling  = directions fitted on real families the model never saw
Sweep    = directions fitted on Computer Modern settings
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare as C  # noqa: E402
import variety as V  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BIG = os.path.join(HERE, "mf_big", "cmss10-axes")
KS = [1, 2, 4, 8, 16, 32, 64, 128]


def main():
    letters = sys.argv[1:] or ["a"]
    out = {}
    for letter in letters:
        rng = np.random.default_rng(C.SEED)
        gen = C.generative(letter, rng)
        perm = rng.permutation(len(gen))
        half = len(gen) // 2
        fit_lines = [gen[i] for i in perm[:half]]
        held_lines = [gen[i] for i in perm[half:]]

        arms = {
            "ceiling_real_families": fit_lines,
            "sweep_cmss10_axes": [l for _, _, l in V.load_corpus(os.path.join(BIG, f"{letter}.txt"), letter)],
            "sweep_cmss10_indep": C.parametric("cmss10-indep", letter),
            "sweep_cmr10_indep": C.parametric("cmr10-indep", letter),
        }
        # every arm fits on the same number of samples
        n_fit = min(len(v) for v in arms.values())
        Xh = V.rasterize_all(held_lines)

        entry = {"held_out": len(held_lines), "n_fit": n_fit, "reach": {}}
        for name, lines in arms.items():
            r = np.random.default_rng(C.SEED)
            sel = [lines[i] for i in r.permutation(len(lines))[:n_fit]]
            X = V.rasterize_all(sel)
            _, Vt, mu = V.pca_spectrum(X)
            entry["reach"][name] = {k: round(float(V.span_fraction(Xh, Vt, mu, k)), 4)
                                    for k in KS if k <= Vt.shape[0]}
        out[letter] = entry

        print(f"--- {letter} --- fit on {n_fit} each, scored on {len(held_lines)} held-out families")
        names = list(arms)
        print(f"{'k':>4} " + "".join(f"{n.replace('sweep_',''):>22}" for n in names))
        for k in KS:
            print(f"{k:>4} " + "".join(
                f"{entry['reach'][n].get(k, float('nan'))*100:>21.1f}%" for n in names))
        print()

    with open(os.path.join(HERE, "control-results.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
