"""score_predictions.py -- hold the harness results up against predictions.md.

Reads the eval and curve JSONs the harness wrote for both arms, applies the
scoring rules registered in predictions.md, and writes
research/predictions-scored.json with every prediction and kill criterion
marked held / failed or triggered / clear.

Run from the repo root, after the harness has scored both arms:
    uv run python projects/pointing/research/score_predictions.py
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "data"))
import strip  # noqa: E402

ARMS = {"regular": "regular-r1", "small": "small-r1"}
SIX = ["period", "comma", "question", "exclamation", "colon", "semicolon"]


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def spearman(a, b):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else 0.0


def train_frequency():
    freq = Counter()
    with open(os.path.join(HERE, "..", "data", "corpus", "train.txt"), encoding="utf-8") as f:
        for line in f:
            slots = line.rstrip("\n").split(strip.SEP)[1]
            freq.update(c for c in slots[0::2] if c != strip.NONE)
    return {strip.MARK_NAMES[m]: freq[m] for m in strip.MARKS}


def rise_order(curve, freq, gold_min=30):
    """-> rows of (mark, train frequency, rise iteration or None, final F1)."""
    last = curve["points"][-1]
    rows = []
    for name in freq:
        if curve["gold_in_sample"].get(name, 0) < gold_min:
            continue
        final = last["f1"][name]
        rise = None
        if final >= 0.05:
            rise = next(p["iter"] for p in curve["points"] if p["f1"][name] >= final / 2)
        rows.append({"mark": name, "train_frequency": freq[name], "rise_iter": rise, "final_f1": final})
    return sorted(rows, key=lambda r: -r["train_frequency"])


def main():
    ev = {arm: load(f"eval-{run}.json") for arm, run in ARMS.items()}
    cv = {arm: load(f"curve-{run}.json") for arm, run in ARMS.items()}
    freq = train_frequency()
    out = {"predictions": {}, "kill_criteria": {}, "train_mark_frequency": freq}
    P = out["predictions"]

    def verdict(ok):
        return "held" if ok else "failed"

    # P1
    r = ev["regular"]
    p1a = r["line_end"]["prose"]["marks"]["."]["recall"]
    p1b = r["per_mark"]["comma"]["f1"]
    P["P1a"] = {"claim": "prose line-end period recall above 95% (2.66M)", "value": p1a, "verdict": verdict(p1a > 0.95)}
    P["P1b"] = {"claim": "comma F1 between 40% and 70% (2.66M)", "value": p1b, "verdict": verdict(0.40 <= p1b <= 0.70)}
    P["verse_line_end_registered_unknown"] = {
        arm: {"accuracy": e["line_end"]["verse"]["accuracy"],
              "marks": {m: {k: v[k] for k in ("precision", "recall", "f1", "share_of_gold")}
                        for m, v in e["line_end"]["verse"]["marks"].items()}}
        for arm, e in ev.items()}

    # P2
    gap = {arm: e["per_mark"]["period"]["recall"] - e["per_mark"]["question"]["recall"] for arm, e in ev.items()}
    P["P2a"] = {"claim": "period recall minus question recall above 20 points (0.79M)", "value": gap["small"],
                "verdict": verdict(gap["small"] > 0.20)}
    P["P2b"] = {"claim": "the same gap under 10 points (2.66M)", "value": gap["regular"],
                "verdict": verdict(gap["regular"] < 0.10)}
    P["P2c"] = {"claim": "question recall in the 10+ bin below the 1-2 bin, Wilson intervals apart"}
    for arm, e in ev.items():
        q = e["question_distance"]
        near, far = q["1-2"], q["10+"]
        ok = far["recall"] < near["recall"] and far["wilson_95"][1] < near["wilson_95"][0]
        P["P2c"][arm] = {"by_distance": {k: {"recall": q[k]["recall"], "gold": q[k]["gold"]} for k in
                                         ["1-2", "3-5", "6-9", "10+", "no question word"] if k in q},
                         "verdict": verdict(ok)}

    # P3
    P["P3a"] = {"claim": "frequency rank predicts rise order, Spearman >= 0.7 (0.79M decides)"}
    for arm in ARMS:
        rows = rise_order(cv[arm], freq)
        never = max(p["iter"] for p in cv[arm]["points"]) + 1
        rho = spearman([-r_["train_frequency"] for r_ in rows], [r_["rise_iter"] or never for r_ in rows])
        P["P3a"][arm] = {"spearman": rho, "marks": rows}
    P["P3a"]["verdict"] = verdict(P["P3a"]["small"]["spearman"] >= 0.7)
    peak = {m: max(p["f1"][m] for p in cv["small"]["points"]) for m in ("colon", "semicolon")}
    P["P3b"] = {"claim": "colon and semicolon F1 under 1% at every snapshot (0.79M)", "peak_f1": peak,
                "verdict": verdict(all(v < 0.01 for v in peak.values()))}

    # P4
    rates = {arm: {"length": e["wellformedness"]["length_error_rate"], "anchor": e["wellformedness"]["anchor_error_rate"]}
             for arm, e in ev.items()}
    worst = max(v for a in rates.values() for v in a.values())
    P["P4"] = {"claim": "length and anchor errors each under 1% on both arms", "rates": rates, "verdict": verdict(worst < 0.01)}

    K = out["kill_criteria"]
    K["kill_1"] = {"rule": "length or anchor errors above 5% on either arm", "worst_rate": worst,
                   "status": "triggered" if worst > 0.05 else "clear"}
    comma = {arm: e["per_mark"]["comma"]["f1"] for arm, e in ev.items()}
    K["kill_2"] = {"rule": "comma F1 under 25% on both arms", "comma_f1": comma,
                   "status": "triggered" if all(v < 0.25 for v in comma.values()) else "clear"}
    diffs = {"exact_match": ev["regular"]["exact_match"]["rate"] - ev["small"]["exact_match"]["rate"]}
    for m in SIX:
        diffs[m] = ev["regular"]["per_mark"][m]["f1"] - ev["small"]["per_mark"][m]["f1"]
    K["kill_3"] = {"rule": "0.79M within 2 points of 2.66M on exact match and all six F1s",
                   "regular_minus_small": diffs,
                   "status": "triggered" if all(abs(v) <= 0.02 for v in diffs.values()) else "clear"}

    path = os.path.join(HERE, "predictions-scored.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    for k, v in P.items():
        if "verdict" in v:
            print(f"{k:<5} {v['verdict']:<7} {v['claim']}  ->  {v.get('value', '')}")
        elif k == "P2c":
            print(f"P2c   regular {v['regular']['verdict']}, small {v['small']['verdict']}")
    for k, v in K.items():
        print(f"{k} {v['status']:<9} {v['rule']}")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
