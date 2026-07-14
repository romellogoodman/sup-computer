"""craft_score.py -- optical-correction rules as a measurement, no training.

Two of type design's checkable craft rules (Dan Hollick, "How to make a font",
https://www.makingsoftware.com/chapters/how-to-make-a-font), run as detectors
over decoded outlines:

  round letters (o c e s)   MUST overshoot -- dip below the baseline (and, in
                            corpus mode, rise above the instance's x-height)
  flat letters (h i l m n u) MUST sit exactly on the baseline

Two modes, one JSON:

  corpus    Gate 0 of the round-2 plan: does the encoded corpus still carry
            overshoot after the 16-unit grid quantized it (typical overshoot
            is ~10-15 em-units -- at or below one grid step)? If the corpus
            can't teach it, no model can learn it and no metric may score it.
  samples   the v1 craft composite over the round-1 sample files (26
            specialists, omni-s, omni-xl at temps 1.0 and 0.8) -- the shape
            metric experiment 09 admitted it lacked. A sampled glyph carries
            no hand context, so only the baseline-side rules apply; the
            x-height side is corpus-mode only.

Pass rules are PRE-REGISTERED here, before any number was looked at:
  round pass = the decoded outline's true y-minimum (quadratic curve extrema
               included) is strictly below y=0
  flat pass  = |y-minimum| <= FLAT_TOL em-units (1/8 grid step, for curve
               feet that bottom out between anchors)
The corpus's own pass rates under the same rules are the reference row every
arm is read against.

Run from the repo root:
    uv run python projects/glyph/craft_score.py            # both modes
    uv run python projects/glyph/craft_score.py corpus
    uv run python projects/glyph/craft_score.py samples
"""
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
import codec  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

ROUND = "oces"       # must overshoot: baseline below, x-height above
FLAT = "hilmnu"      # must sit flat on the baseline
XREF = "xzuvw"       # flat-topped letters; median top = the instance's x-height

# v1.1 amendment, adopted AFTER corpus mode falsified u's placement: 84.8% of
# corpus instances dip u below the baseline -- its bowl bottom behaves like a
# round letter's, not a stem foot. v1 numbers stay reported (the rules were
# pre-registered); v1.1 is the corrected instrument.
ROUND_11 = ROUND + "u"
FLAT_11 = "hilmn"
GRID = codec.GRID    # 16 em-units -- one coordinate step
FLAT_TOL = 2         # em-units; 1/8 grid step

SAMPLE_ARMS = {
    "case": [(f"runs/{ch}-r1/samples-{ch}-t1.0.txt", 1.0) for ch in codec.LETTERS],
    "omni-s": [("runs/omni-s-r1/samples-abcdefghijklmnopqrstuvwxyz-t1.0.txt", 1.0)],
    "omni-xl": [("runs/omni-xl-r1/samples-abcdefghijklmnopqrstuvwxyz-t1.0.txt", 1.0)],
    "omni-xl@0.8": [("runs/omni-xl-r1/samples-abcdefghijklmnopqrstuvwxyz-t0.8.txt", 0.8)],
}


# --- exact vertical extrema of a decoded glyph ------------------------------

def _quad_extremum(y0, yc, y1):
    """Interior y-extremum of a quadratic Bezier, or None if monotone."""
    d = y0 - 2 * yc + y1
    if d == 0:
        return None
    t = (y0 - yc) / d
    if not 0 < t < 1:
        return None
    return (1 - t) ** 2 * y0 + 2 * t * (1 - t) * yc + t ** 2 * y1


def y_extrema(decoded):
    """(ymin, ymax) of the outline, including quadratic curve extrema --
    a bowl's true bottom usually lies between two on-curve anchors."""
    ys = []
    for contour in decoded["contours"]:
        prev = None
        for seg in contour:
            if seg[0] == "M":
                prev = seg[1]
                ys.append(prev[1])
            elif seg[0] == "L":
                prev = seg[1]
                ys.append(prev[1])
            else:  # Q: control, endpoint
                (_, cy), (_, py) = seg[1], seg[2]
                e = _quad_extremum(prev[1], cy, py)
                if e is not None:
                    ys.append(e)
                ys.append(py)
                prev = seg[2]
    return min(ys), max(ys)


def round_pass(ymin):
    return ymin < 0


def flat_pass(ymin):
    return abs(ymin) <= FLAT_TOL


# --- corpus mode: Gate 0 -----------------------------------------------------

def read_corpus():
    """corpus/<letter>.txt -> {(family_dir, source): {letter: decoded}}."""
    instances = {}
    for letter in ROUND + FLAT + XREF:
        with open(os.path.join(HERE, "data", "corpus", f"{letter}.txt")) as f:
            for row in f:
                family_dir, source, line = row.rstrip("\n").split("\t")
                instances.setdefault((family_dir, source), {})[letter] = codec.decode_glyph(line)
    return instances


def corpus_mode():
    instances = read_corpus()
    # u gets round-letter measurements too -- it's the letter whose placement
    # the corpus is allowed to falsify (see the v1.1 note above)
    per_letter = {ch: {"n": 0, "dip_any": 0, "dip_half": 0, "dip_full": 0,
                       "top_any": 0, "top_half": 0, "top_full": 0,
                       "dips": []} for ch in ROUND_11}
    flat_letter = {ch: {"n": 0, "flat": 0, "dip_any": 0, "dips": 0, "floats": 0} for ch in FLAT}

    n_instances = 0
    for glyphs in instances.values():
        refs = [y_extrema(glyphs[ch])[1] for ch in XREF if ch in glyphs]
        if len(refs) < 2:
            continue
        n_instances += 1
        xh = statistics.median(refs)
        for ch in ROUND_11:
            if ch not in glyphs:
                continue
            ymin, ymax = y_extrema(glyphs[ch])
            dip, top = -ymin, ymax - xh
            s = per_letter[ch]
            s["n"] += 1
            s["dip_any"] += dip > 0
            s["dip_half"] += dip >= GRID / 2
            s["dip_full"] += dip >= GRID
            s["top_any"] += top > 0
            s["top_half"] += top >= GRID / 2
            s["top_full"] += top >= GRID
            if dip > 0:
                s["dips"].append(dip)
        for ch in FLAT:
            if ch not in glyphs:
                continue
            ymin, _ = y_extrema(glyphs[ch])
            s = flat_letter[ch]
            s["n"] += 1
            s["flat"] += flat_pass(ymin)
            s["dip_any"] += ymin < 0  # same rule the round letters are held to
            s["dips"] += ymin < -FLAT_TOL
            s["floats"] += ymin > FLAT_TOL

    result = {"n_instances": n_instances, "round": {}, "flat": {}}
    for ch, s in per_letter.items():
        n = s["n"]
        result["round"][ch] = {
            "n": n,
            "dip_any": round(s["dip_any"] / n, 4),
            "dip_half_step": round(s["dip_half"] / n, 4),
            "dip_full_step": round(s["dip_full"] / n, 4),
            "top_any": round(s["top_any"] / n, 4),
            "top_half_step": round(s["top_half"] / n, 4),
            "top_full_step": round(s["top_full"] / n, 4),
            "median_dip_when_present": round(statistics.median(s["dips"]), 1) if s["dips"] else None,
        }
    for ch, s in flat_letter.items():
        n = s["n"]
        result["flat"][ch] = {"n": n, "flat": round(s["flat"] / n, 4),
                              "dip_any": round(s["dip_any"] / n, 4),
                              "dips": round(s["dips"] / n, 4), "floats": round(s["floats"] / n, 4)}

    # the corpus scored as if it were an arm -- the reference row for samples
    def ref(round_set, flat_set):
        rp = sum(per_letter[ch]["dip_any"] for ch in round_set)
        rn = sum(per_letter[ch]["n"] for ch in round_set)
        fp = sum(flat_letter[ch]["flat"] for ch in flat_set)
        fn = sum(flat_letter[ch]["n"] for ch in flat_set)
        return {"round_pass": round(rp / rn, 4), "flat_pass": round(fp / fn, 4),
                "craft_pass": round((rp + fp) / (rn + fn), 4)}

    result["reference_row"] = ref(ROUND, FLAT)
    result["reference_row_v1_1"] = ref(ROUND_11, FLAT_11)
    return result


# --- samples mode: the v1 composite over round-1 output ----------------------

def score_samples(paths, round_set, flat_set):
    per_letter = {}
    for rel, _temp in paths:
        with open(os.path.join(HERE, rel)) as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue
                letter = line[0]
                s = per_letter.setdefault(letter, {"n": 0, "valid": 0,
                                                   "scored": 0, "pass": 0})
                s["n"] += 1
                try:
                    decoded = codec.decode_glyph(line)
                except codec.GlyphSyntaxError:
                    continue
                s["valid"] += 1
                ymin, _ = y_extrema(decoded)
                if letter in round_set:
                    s["scored"] += 1
                    s["pass"] += round_pass(ymin)
                elif letter in flat_set:
                    s["scored"] += 1
                    s["pass"] += flat_pass(ymin)
    return per_letter


def samples_mode(round_set=ROUND, flat_set=FLAT, label="v1"):
    result = {}
    for arm, paths in SAMPLE_ARMS.items():
        per_letter = score_samples(paths, round_set, flat_set)
        n = sum(s["n"] for s in per_letter.values())
        valid = sum(s["valid"] for s in per_letter.values())
        rs = [per_letter[ch] for ch in round_set if ch in per_letter]
        fs = [per_letter[ch] for ch in flat_set if ch in per_letter]
        r_scored, r_pass = sum(s["scored"] for s in rs), sum(s["pass"] for s in rs)
        f_scored, f_pass = sum(s["scored"] for s in fs), sum(s["pass"] for s in fs)
        result[arm] = {
            "samples": n,
            "parse_rate": round(valid / n, 4),
            "round_pass_of_valid": round(r_pass / r_scored, 4) if r_scored else None,
            "flat_pass_of_valid": round(f_pass / f_scored, 4) if f_scored else None,
            "craft_pass_of_valid": round((r_pass + f_pass) / (r_scored + f_scored), 4)
                                   if r_scored + f_scored else None,
            "per_letter": {ch: {"valid": f"{s['valid']}/{s['n']}",
                                "pass": f"{s['pass']}/{s['scored']}"}
                           for ch, s in sorted(per_letter.items())
                           if ch in round_set + flat_set},
        }
        print(f"[{label}] {arm}: parse {result[arm]['parse_rate']:.1%}  "
              f"round-pass {result[arm]['round_pass_of_valid']:.1%}  "
              f"flat-pass {result[arm]['flat_pass_of_valid']:.1%}  "
              f"craft {result[arm]['craft_pass_of_valid']:.1%}  (of {valid} valid)")
    return result


def main():
    modes = sys.argv[1:] or ["corpus", "samples"]
    out_path = os.path.join(HERE, "research", "craft-results.json")
    results = {}
    if os.path.exists(out_path):
        with open(out_path) as f:
            results = json.load(f)
    results["rules"] = {
        "round_letters": ROUND, "flat_letters": FLAT, "xheight_ref_letters": XREF,
        "round_pass": "true y-min of decoded outline (curve extrema included) < 0",
        "flat_pass": f"|y-min| <= {FLAT_TOL} em-units (1/8 grid step)",
        "grid_step_em_units": GRID,
        "source": "https://www.makingsoftware.com/chapters/how-to-make-a-font",
    }
    if "corpus" in modes:
        print("corpus mode (Gate 0)...")
        results["corpus"] = corpus_mode()
        ref = results["corpus"]["reference_row"]
        print(f"corpus reference row: round-pass {ref['round_pass']:.1%}  "
              f"flat-pass {ref['flat_pass']:.1%}  "
              f"({results['corpus']['n_instances']} instances)")
        for ch, s in results["corpus"]["round"].items():
            print(f"  {ch}: dip any {s['dip_any']:.1%}  half-step {s['dip_half_step']:.1%}  "
                  f"full-step {s['dip_full_step']:.1%}  top any {s['top_any']:.1%}  "
                  f"median dip {s['median_dip_when_present']}")
    if "samples" in modes:
        print("samples mode (round-1 arms)...")
        results["samples"] = samples_mode()
        results["samples_v1_1"] = samples_mode(ROUND_11, FLAT_11, label="v1.1")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=1)
    print(f"wrote {os.path.relpath(out_path)}")


if __name__ == "__main__":
    main()
