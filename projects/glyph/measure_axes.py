"""measure_axes.py -- can three typographic axes explain the generalist's
"unexplained variance"?

Type design already standardized how hands differ (Dan Hollick, "How to make
a font", https://www.makingsoftware.com/chapters/how-to-make-a-font): weight
(Bigelow's ratio of x-height to vertical stem thickness -- a regular sits
near 1:5-1:6), x-height ratio, and width. Round 1's omni-xl carried 759
families as unexplained variance; the round-2 plan proposes conditioning on
these axes. This measures the premise with no training:

  1. every axis, per instance, from the ENCODED corpus itself -- measured on
     what the model actually sees, post-quantization. The corpus is
     lowercase-only, so the x-height ratio normalizes to the ascender line
     (no cap height exists here); the chapter's cap-height framing is noted
     in the report.
  2. the declared-weight cross-check the plan's Gate 1 asks for: parsed
     @wghtNNN instance labels (plus manifest weights for static files) vs
     measured stems -- Spearman overall, plus per-family monotonicity.
  3. per-instance BPC of the frozen round-1 omni-xl over held-out (test)
     families, scored per line, letter-centered so "this hand is hard"
     isn't confounded with "this instance is missing easy letters" -- then
     an OLS of instance effect on the three axes. The R^2 is the premise's
     number: near zero and conditioning's biggest arm dies.

Also emits the round-2 plan's Gate-1 deliverable: corpus-quantile bin edges
(weight 5, x-height 3, width 3).

Writes research/axes-instances.json (per-instance measurements) and
research/axes-results.json (aggregates, bins, cross-check, regression).

Run from the repo root:
    uv run python projects/glyph/measure_axes.py
    uv run python projects/glyph/measure_axes.py --no-bpc   # axes only, no model
"""
import hashlib
import json
import math
import os
import statistics
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
import codec  # noqa: E402
from craft_score import y_extrema  # noqa: E402  (same exact-extrema geometry)

HERE = os.path.dirname(os.path.abspath(__file__))

XREF = "xzuvw"    # flat-topped letters; median top = x-height
ASC = "bdhkl"     # ascender letters; median top = ascender line
STEM = "li"       # scanline letters for stem thickness
BLOCK_SIZE = 512  # matches prepare.py; overlong lines were never trained on
BINS = {"weight_ratio": 5, "xh_ratio": 3, "width": 3}  # round-2 plan, lever 1


def split_of(family_dir):
    """prepare.py's family-split rule, verbatim: md5 % 10 -> 8 val, 9 test."""
    h = int(hashlib.md5(family_dir.encode()).hexdigest(), 16) % 10
    return "train" if h < 8 else ("val" if h == 8 else "test")


# --- stem thickness: horizontal scanline through a stem letter ---------------

def _crossings(decoded, h):
    """x-positions where the outline crosses the horizontal line y=h."""
    xs = []
    for contour in decoded["contours"]:
        pts = []
        prev = None
        for seg in contour:
            if seg[0] == "M":
                prev = seg[1]
            elif seg[0] == "L":
                pts.append(("L", prev, seg[1]))
                prev = seg[1]
            else:
                pts.append(("Q", prev, seg[1], seg[2]))
                prev = seg[2]
        first = contour[0][1]
        pts.append(("L", prev, first))  # Z closes with a straight edge
        for p in pts:
            if p[0] == "L":
                (x0, y0), (x1, y1) = p[1], p[2]
                if (y0 - h) * (y1 - h) < 0:
                    t = (h - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            else:
                (x0, y0), (cx, cy), (x1, y1) = p[1], p[2], p[3]
                a, b, c = y0 - 2 * cy + y1, 2 * (cy - y0), y0 - h
                if abs(a) < 1e-9:
                    if abs(b) > 1e-9:
                        t = -c / b
                        if 0 <= t < 1:
                            xs.append((1 - t) ** 2 * x0 + 2 * t * (1 - t) * cx + t ** 2 * x1)
                else:
                    disc = b * b - 4 * a * c
                    if disc >= 0:
                        r = math.sqrt(disc)
                        for t in ((-b + r) / (2 * a), (-b - r) / (2 * a)):
                            if 0 <= t < 1:
                                xs.append((1 - t) ** 2 * x0 + 2 * t * (1 - t) * cx + t ** 2 * x1)
    return sorted(xs)


def stem_width(decoded, xh):
    """Widest even-odd filled span on a scanline at half x-height (the l/i
    stem). Tangencies make an odd crossing count; nudge and retry."""
    for h in (xh / 2, xh / 2 + 3, xh / 2 - 3, xh / 2 + 7):
        xs = _crossings(decoded, h)
        if len(xs) >= 2 and len(xs) % 2 == 0:
            return max(xs[i + 1] - xs[i] for i in range(0, len(xs), 2))
    return None


# --- axes over the whole corpus ----------------------------------------------

def read_corpus():
    """corpus/<letter>.txt -> {(family, source): {letter: line}} (all 26)."""
    instances = {}
    for letter in codec.LETTERS:
        with open(os.path.join(HERE, "data", "corpus", f"{letter}.txt")) as f:
            for row in f:
                family_dir, source, line = row.rstrip("\n").split("\t")
                instances.setdefault((family_dir, source), {})[letter] = line
    return instances


def declared_weights():
    """(family, source) label -> declared weight: @wghtNNN if present, else
    the manifest's per-file weight."""
    with open(os.path.join(HERE, "data", "manifest.json")) as f:
        manifest = json.load(f)
    file_weight = {}
    for fam in manifest["families"]:
        for file in fam["files"]:
            file_weight[(fam["dir"], file["filename"])] = file.get("weight")
    return file_weight


def measure_instances(instances):
    file_weight = declared_weights()
    rows, skipped = [], 0
    for (family, source), lines in sorted(instances.items()):
        decoded = {}
        for ch in set(XREF + ASC + STEM):
            if ch in lines:
                try:
                    decoded[ch] = codec.decode_glyph(lines[ch])
                except codec.GlyphSyntaxError:
                    pass
        xrefs = [y_extrema(decoded[ch])[1] for ch in XREF if ch in decoded]
        ascs = [y_extrema(decoded[ch])[1] for ch in ASC if ch in decoded]
        if len(xrefs) < 2 or len(ascs) < 2:
            skipped += 1
            continue
        xh, asc = statistics.median(xrefs), statistics.median(ascs)
        stems = [w for ch in STEM if ch in decoded
                 for w in [stem_width(decoded[ch], xh)] if w]
        if not stems or xh <= 0 or asc <= xh:
            skipped += 1
            continue
        stem = statistics.median(stems)
        advs = [codec.unbucket(line[1]) for line in lines.values()]
        if "@wght" in source:
            wght = int(source.rsplit("@wght", 1)[1])
        else:
            wght = file_weight.get((family, source))
        rows.append({
            "family": family, "source": source, "split": split_of(family),
            "xh": round(xh, 1), "asc": round(asc, 1),
            "stem": round(stem, 1),
            "weight_ratio": round(xh / stem, 2),   # Bigelow: regular ~5-6
            "xh_ratio": round(xh / asc, 3),
            "width": round(sum(advs) / len(advs) / codec.EM, 3),
            # not a craft axis -- the complexity confound the regression
            # reads the axes against
            "mean_len": round(sum(len(ln) for ln in lines.values()) / len(lines), 1),
            "declared_wght": wght,
        })
    return rows, skipped


# --- declared-weight cross-check ----------------------------------------------

def spearman(a, b):
    def rank(v):
        """Average ranks for ties -- declared weights are heavily tied."""
        v = np.asarray(v, float)
        order = np.argsort(v)
        ranks = np.empty(len(v))
        sv = v[order]
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and sv[j + 1] == sv[i]:
                j += 1
            ranks[order[i:j + 1]] = (i + j) / 2
            i = j + 1
        return ranks
    ra, rb = rank(a), rank(b)
    ra, rb = ra - ra.mean(), rb - rb.mean()
    return float((ra * rb).sum() / math.sqrt((ra ** 2).sum() * (rb ** 2).sum()))


def weight_crosscheck(rows):
    with_wght = [r for r in rows if r["declared_wght"]]
    overall = spearman([r["declared_wght"] for r in with_wght],
                       [r["stem"] / r["xh"] for r in with_wght])
    fams = {}
    for r in with_wght:
        fams.setdefault(r["family"], []).append(r)
    multi = {f: rs for f, rs in fams.items()
             if len({r["declared_wght"] for r in rs}) >= 3}
    monotone = sum(
        1 for rs in multi.values()
        if [r["stem"] for r in sorted(rs, key=lambda r: r["declared_wght"])]
        == sorted(r["stem"] for r in rs))
    # oddballs: heavy declared weight, hairline measured stem (or the reverse)
    dw = np.array([r["declared_wght"] for r in with_wght], float)
    ms = np.array([r["stem"] / r["xh"] for r in with_wght], float)
    zdiff = (dw - dw.mean()) / dw.std() - (ms - ms.mean()) / ms.std()
    zs = [with_wght[i] for i in np.argsort(zdiff)]
    odd = [f"{r['family']}/{r['source']}: declared {r['declared_wght']}, "
           f"stem {r['stem']} on xh {r['xh']}" for r in zs[:5] + zs[-5:]]
    return {"n": len(with_wght), "spearman_declared_vs_stem": round(overall, 3),
            "families_with_3plus_weights": len(multi),
            "perfectly_monotone": monotone,
            "oddballs_inspect": odd}


# --- per-instance BPC of the frozen omni-xl over test families ---------------

def instance_bpc(rows, instances):
    import torch  # noqa: PLC0415 -- keep --no-bpc runs torch-free

    from nanogpt_core.checkpoint import load_model, load_tokenizer

    model, ckpt = load_model("projects/glyph/runs/omni-xl-r1")
    tok = load_tokenizer(ckpt, "projects/glyph/data")
    device = next(model.parameters()).device
    stoi = tok.meta["stoi"]
    nl = stoi["\n"]

    seen = set()
    for (family, _), lines in instances.items():
        if split_of(family) != "test":
            for line in lines.values():
                seen.add(line)

    test_keys = [k for k in instances if split_of(k[0]) == "test"]
    work, contaminated, overlong = [], 0, 0
    for key in test_keys:
        for ch, line in instances[key].items():
            if line in seen:
                contaminated += 1
                continue
            if len(line) + 1 > BLOCK_SIZE:
                overlong += 1
                continue
            work.append((key, ch, line))
    work.sort(key=lambda w: len(w[2]))

    per_line = []  # (key, letter, bpc)
    ln2 = math.log(2)
    with torch.no_grad():
        for i in range(0, len(work), 64):
            batch = work[i:i + 64]
            texts = ["\n" + line + "\n" for _, _, line in batch]
            width = max(len(t) for t in texts)
            x = torch.full((len(batch), width - 1), nl, dtype=torch.long)
            y = torch.full((len(batch), width - 1), -1, dtype=torch.long)
            for j, t in enumerate(texts):
                ids = [stoi[c] for c in t]
                x[j, :len(ids) - 1] = torch.tensor(ids[:-1])
                y[j, :len(ids) - 1] = torch.tensor(ids[1:])
            logits, _ = model(x.to(device), y.to(device))
            flat = torch.nn.functional.cross_entropy(
                logits.view(-1, logits.size(-1)), y.view(-1).to(device),
                ignore_index=-1, reduction="none").view(len(batch), -1).cpu()
            for j, (key, ch, line) in enumerate(batch):
                n = len(line) + 1  # the line's own chars + its newline
                # padded positions carry loss 0.0 (ignore_index), so the
                # full-row sum is exactly the line's NLL over its n chars
                per_line.append((key, ch, flat[j].sum().item() / n / ln2))
            if i % 1024 == 0:
                print(f"  scored {i + len(batch)}/{len(work)} lines")

    letter_mean = {}
    for _, ch, bpc in per_line:
        letter_mean.setdefault(ch, []).append(bpc)
    letter_mean = {ch: sum(v) / len(v) for ch, v in letter_mean.items()}

    agg = {}
    for key, ch, bpc in per_line:
        a = agg.setdefault(key, {"raw": [], "centered": []})
        a["raw"].append(bpc)
        a["centered"].append(bpc - letter_mean[ch])
    by_key = {r["family"] + "\t" + r["source"]: r for r in rows}
    n_matched = 0
    for (family, source), a in agg.items():
        r = by_key.get(family + "\t" + source)
        if r is not None and len(a["raw"]) >= 20:  # near-complete alphabets only
            r["bpc"] = round(sum(a["raw"]) / len(a["raw"]), 4)
            r["bpc_centered"] = round(sum(a["centered"]) / len(a["centered"]), 4)
            n_matched += 1
    return {"test_instances_scored": n_matched, "lines_scored": len(per_line),
            "contaminated_dropped": contaminated, "overlong_dropped": overlong}


def regression(rows):
    scored = [r for r in rows if "bpc_centered" in r]
    axes = ["weight_ratio", "xh_ratio", "width"]
    X = np.array([[r[a] for a in axes] for r in scored], float)
    Xs = (X - X.mean(0)) / X.std(0)
    out = {"n": len(scored), "axes": axes}
    for target in ("bpc_centered", "bpc"):
        y = np.array([r[target] for r in scored], float)
        yc = y - y.mean()
        A = np.hstack([Xs, np.ones((len(Xs), 1))])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        resid = y - A @ coef
        r2 = 1 - (resid ** 2).sum() / (yc ** 2).sum()
        uni = {}
        for i, a in enumerate(axes):
            c = float(np.corrcoef(Xs[:, i], y)[0, 1])
            uni[a] = {"r": round(c, 3), "r2": round(c * c, 3)}
        out[target] = {"r2_all_three": round(float(r2), 3),
                       "std_coefs": {a: round(float(coef[i]), 4) for i, a in enumerate(axes)},
                       "univariate": uni}
    out["axis_correlations"] = {
        f"{a}~{b}": round(float(np.corrcoef(Xs[:, i], Xs[:, j])[0, 1]), 3)
        for i, a in enumerate(axes) for j, b in enumerate(axes) if i < j}

    # the competing explanation: outline complexity, not design axes
    L = np.array([r["mean_len"] for r in scored], float)
    for target in ("bpc_centered", "bpc"):
        y = np.array([r[target] for r in scored], float)
        c = float(np.corrcoef(L, y)[0, 1])
        out[target]["complexity_mean_len"] = {"r": round(c, 3), "r2": round(c * c, 3)}
    return out


def quantile_bins(rows):
    edges = {}
    for axis, k in BINS.items():
        v = np.array([r[axis] for r in rows], float)
        edges[axis] = [round(float(np.quantile(v, q / k)), 3) for q in range(k + 1)]
    return edges


def main():
    do_bpc = "--no-bpc" not in sys.argv
    print("reading corpus...")
    instances = read_corpus()
    print(f"measuring axes over {len(instances)} instances...")
    rows, skipped = measure_instances(instances)
    print(f"measured {len(rows)} instances ({skipped} skipped: missing refs or no stem)")

    results = {
        "n_measured": len(rows), "n_skipped": skipped,
        "source": "https://www.makingsoftware.com/chapters/how-to-make-a-font",
        "axis_summary": {
            axis: {"min": min(r[axis] for r in rows), "median": round(statistics.median(r[axis] for r in rows), 3),
                   "max": max(r[axis] for r in rows)}
            for axis in ("weight_ratio", "xh_ratio", "width")},
        "quantile_bin_edges": quantile_bins(rows),
        "declared_weight_crosscheck": weight_crosscheck(rows),
    }
    print(f"weight ratio (xh:stem) median {results['axis_summary']['weight_ratio']['median']}  "
          f"(Bigelow: regular ~5-6)")
    print(f"declared-weight cross-check: Spearman "
          f"{results['declared_weight_crosscheck']['spearman_declared_vs_stem']}  "
          f"monotone families {results['declared_weight_crosscheck']['perfectly_monotone']}"
          f"/{results['declared_weight_crosscheck']['families_with_3plus_weights']}")

    if do_bpc:
        print("scoring per-line BPC of frozen omni-xl over test families...")
        results["bpc_scoring"] = instance_bpc(rows, instances)
        results["regression"] = regression(rows)
        reg = results["regression"]
        print(f"regression over {reg['n']} test instances:")
        print(f"  centered instance effect ~ 3 axes: R^2 = {reg['bpc_centered']['r2_all_three']}")
        print("  univariate: " + "  ".join(
            f"{a} r2={reg['bpc_centered']['univariate'][a]['r2']}" for a in reg["axes"]))

    with open(os.path.join(HERE, "research", "axes-instances.json"), "w") as f:
        json.dump(rows, f, indent=0)
    with open(os.path.join(HERE, "research", "axes-results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("wrote research/axes-instances.json, research/axes-results.json")


if __name__ == "__main__":
    main()
