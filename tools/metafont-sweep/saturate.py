"""
saturate.py -- does a corpus stop teaching you anything?

Compress N glyphs together with a dictionary large enough to span the whole
corpus (lzma, 64MB dict), and watch the marginal cost of the Nth glyph. A
corpus of near-duplicates gets cheap per glyph and stays cheap; a corpus of
genuinely different objects keeps paying full price.

Reported as bytes-per-glyph normalized by that arm's own mean raw glyph size,
so an arm whose outlines are simply more complex isn't credited for it.
"""
import json
import lzma
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare as C  # noqa: E402

FILTERS = [{"id": lzma.FILTER_LZMA2, "preset": 9, "dict_size": 1 << 26}]


def squeeze(lines):
    raw = "\n".join(lines).encode()
    comp = lzma.compress(raw, format=lzma.FORMAT_RAW, filters=FILTERS)
    return len(raw), len(comp)


def curve(lines, rng, points=14):
    order = rng.permutation(len(lines))
    ns = np.unique(np.geomspace(8, len(lines), points).astype(int))
    out = []
    for n in ns:
        sel = [lines[i] for i in order[:n]]
        rawb, compb = squeeze(sel)
        out.append({"n": int(n), "raw": rawb, "comp": compb,
                    "comp_per_glyph": round(compb / n, 2),
                    "ratio": round(compb / rawb, 4)})
    # marginal cost of the last stretch, normalized by raw bytes per glyph
    a, b = out[-2], out[-1]
    dn = b["n"] - a["n"]
    marginal = (b["comp"] - a["comp"]) / dn
    raw_per_glyph = b["raw"] / b["n"]
    return out, round(marginal, 2), round(marginal / raw_per_glyph, 4)


def main():
    letters = sys.argv[1:] or ["a"]
    arms = ["cmss10-axes", "cmss10-indep", "cmr10-indep"]
    report = {}
    for letter in letters:
        rng = np.random.default_rng(C.SEED)
        gen = C.generative(letter, rng)
        par = {a: C.parametric(a, letter) for a in arms}
        par = {a: v for a, v in par.items() if v}
        n = min([len(gen)] + [len(v) for v in par.values()])

        entry = {}
        sets = {"generative": [gen[i] for i in rng.permutation(len(gen))[:n]]}
        for a, v in par.items():
            sets[a] = [v[i] for i in rng.permutation(len(v))[:n]]

        print(f"--- {letter} (n={n} per arm) ---")
        print(f"{'arm':<16} {'comp/glyph':>11} {'ratio':>7} {'marginal':>9} {'marginal/raw':>13}")
        for a, lines in sets.items():
            pts, marg, marg_norm = curve(lines, np.random.default_rng(C.SEED))
            entry[a] = {"curve": pts, "marginal": marg, "marginal_over_raw": marg_norm}
            print(f"{a:<16} {pts[-1]['comp_per_glyph']:>11} {pts[-1]['ratio']:>7} "
                  f"{marg:>9} {marg_norm:>13}")
        print()
        report[letter] = entry

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "saturate-results.json"), "w") as f:
        json.dump(report, f, indent=1)


if __name__ == "__main__":
    main()
