"""
compare.py -- the parametric arms against the generative one.

Generative arm: one glyph per google/fonts family (one designer, one sample).
Parametric arms: settings of Knuth's Computer Modern program.

Reported per arm: intrinsic dimensionality, saturation, unigram BPC. Across
arms: how much of the generative corpus's variance the parametric corpus can
reach, and how much of it the two share directions for.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import variety as V  # noqa: E402

GF = os.path.join(V.GLYPH_DATA, "corpus")
MF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mf_corpus")
SEED = 1729


def generative(letter, rng):
    """One glyph per family -- a designer counted once, not once per weight."""
    rows = V.load_corpus(os.path.join(GF, f"{letter}.txt"), letter)
    by_fam = {}
    for fam, src, line in rows:
        by_fam.setdefault(fam, []).append(line)
    fams = sorted(by_fam)
    return [by_fam[f][rng.integers(len(by_fam[f]))] for f in fams]


def parametric(arm, letter):
    path = os.path.join(MF, arm, f"{letter}.txt")
    if not os.path.exists(path):
        return []
    return [line for _, _, line in V.load_corpus(path, letter)]


def subspace_report(Xg, Xp, ks):
    """Two views of 'can the parameter space get there'.

    reach   -- generative glyphs measured from the parametric corpus's own
               centre, along its own directions: could a sweep produce them?
    overlap -- each arm centred on itself: do they vary in the same directions
               at all, setting aside that they sit in different places?
    """
    _, Vtp, mup = V.pca_spectrum(Xp)
    mug = Xg.mean(axis=0)
    out = {"reach": {}, "overlap": {}}
    for k in ks:
        if k > Vtp.shape[0]:
            continue
        out["reach"][k] = round(float(V.span_fraction(Xg, Vtp, mup, k)), 4)
        out["overlap"][k] = round(float(V.span_fraction(Xg, Vtp, mug, k)), 4)
    return out


def main():
    letters = sys.argv[1:] or ["a"]
    arms = ["cmss10-axes", "cmss10-indep", "cmr10-indep"]
    report = {}

    for letter in letters:
        rng = np.random.default_rng(SEED)
        gen = generative(letter, rng)
        par = {a: parametric(a, letter) for a in arms}
        par = {a: v for a, v in par.items() if v}
        n_match = min([len(gen)] + [len(v) for v in par.values()])

        Xg_full = V.rasterize_all(gen)
        ratios_g, _, _ = V.pca_spectrum(Xg_full)
        entry = {
            "n": {"generative": len(gen), **{a: len(v) for a, v in par.items()}},
            "matched_n": n_match,
            "dims": {"generative_full": V.dims_for(ratios_g)},
            "bpc": {"generative": round(V.unigram_bpc(gen), 4)},
            "saturation": {"generative": V.saturation(gen, rng)},
            "subspace": {},
        }

        # matched-N dimensionality, so the comparison isn't a sample-size artifact
        idx = rng.permutation(len(gen))[:n_match]
        Xg = Xg_full[idx]
        rg, _, _ = V.pca_spectrum(Xg)
        entry["dims"]["generative_matched"] = V.dims_for(rg)

        for arm, lines in par.items():
            Xp_full = V.rasterize_all(lines)
            rp_full, _, _ = V.pca_spectrum(Xp_full)
            entry["dims"][arm + "_full"] = V.dims_for(rp_full)
            jdx = rng.permutation(len(lines))[:n_match]
            Xp = Xp_full[jdx]
            rp, _, _ = V.pca_spectrum(Xp)
            entry["dims"][arm + "_matched"] = V.dims_for(rp)
            entry["bpc"][arm] = round(V.unigram_bpc(lines), 4)
            entry["saturation"][arm] = V.saturation(lines, rng)
            entry["subspace"][arm] = subspace_report(Xg, Xp, [1, 2, 4, 8, 16, 32, 64])

        report[letter] = entry
        print(f"--- {letter} ---")
        print(json.dumps({k: v for k, v in entry.items() if k != "saturation"}, indent=1))

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "compare-results.json"), "w") as f:
        json.dump(report, f, indent=1)


if __name__ == "__main__":
    main()
