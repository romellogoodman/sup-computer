"""precheck.py -- is the null clean? Chi-square tests on the draws themselves.

Run BEFORE any training. Older draw machines were not always fair, so the
studio checks the corpus against uniform before a model is asked to. If a
test fails here, the model's result is written against that, not around it.

Pick 3 (the check the design asks for), per era (evening 1976 on, midday
1995 on) and per decade inside each era:
  - digit frequency by position (3 tests, df 9 each)
  - all 1,000 combinations (df 999), whole era only
  - lag-1 dependence: digit at position p in one draw against the same
    position in the next draw of the same era (3 tests, df 81 each)

Powerball (a cheap extra):
  - red ball frequency (df 25)
  - white ball frequency (df 68). Five whites leave the drum without
    replacement, so the usual statistic is scaled by (69-1)/(69-5).

Every p-value is reported. The threshold is Bonferroni: 0.05 divided by the
number of tests run. Stdlib only.

Run from the repo root:
    uv run python projects/lucky/precheck.py     # -> research/precheck.json
"""

import csv
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def chi2_sf(x, df):
    """Upper tail of the chi-square distribution, Q(df/2, x/2)."""
    a, x = df / 2.0, x / 2.0
    if x <= 0:
        return 1.0
    lg = math.lgamma(a)
    if x < a + 1:  # series for P, return 1 - P
        term = total = 1.0 / a
        n = a
        for _ in range(100000):
            n += 1
            term *= x / n
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return max(0.0, 1.0 - total * math.exp(-x + a * math.log(x) - lg))
    # continued fraction for Q (modified Lentz)
    tiny = 1e-300
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, 100000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return min(1.0, math.exp(-x + a * math.log(x) - lg) * h)


def gof(counts, scale=1.0):
    """Chi-square goodness of fit against uniform."""
    n, k = sum(counts), len(counts)
    e = n / k
    stat = sum((c - e) ** 2 / e for c in counts) * scale
    return {"chi2": round(stat, 3), "df": k - 1, "p": chi2_sf(stat, k - 1), "n": n}


def independence(pairs, k=10):
    """Chi-square test of independence on a k x k table of (a, b) pairs."""
    table = [[0] * k for _ in range(k)]
    for a, b in pairs:
        table[a][b] += 1
    n = len(pairs)
    rows = [sum(r) for r in table]
    cols = [sum(table[i][j] for i in range(k)) for j in range(k)]
    stat = sum((table[i][j] - rows[i] * cols[j] / n) ** 2 / (rows[i] * cols[j] / n)
               for i in range(k) for j in range(k))
    df = (k - 1) ** 2
    return {"chi2": round(stat, 3), "df": df, "p": chi2_sf(stat, df), "n": n}


def pick3_tests(draws, label, combos):
    """draws: list of 3-digit strings in time order."""
    out = []
    for p in range(3):
        counts = [0] * 10
        for d in draws:
            counts[int(d[p])] += 1
        out.append({"test": f"{label} · position {p + 1} frequency", "counts": counts, **gof(counts)})
    if combos:
        counts = [0] * 1000
        for d in draws:
            counts[int(d)] += 1
        out.append({"test": f"{label} · 1,000 combinations", **gof(counts)})
        for p in range(3):
            pairs = [(int(a[p]), int(b[p])) for a, b in zip(draws, draws[1:])]
            out.append({"test": f"{label} · position {p + 1} lag-1 dependence", **independence(pairs)})
    return out


def main():
    tests = []
    with open(os.path.join(HERE, "data", "pick3", "draws.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    for era in ("evening", "midday"):
        era_rows = [r for r in rows if r["draw"] == era]
        tests += pick3_tests([r["digits"] for r in era_rows],
                             f"pick 3 {era} {era_rows[0]['date'][:4]}–{era_rows[-1]['date'][:4]}", combos=True)
        decades = sorted({r["date"][:3] for r in era_rows})
        for dec in decades:
            sub = [r["digits"] for r in era_rows if r["date"][:3] == dec]
            tests += pick3_tests(sub, f"pick 3 {era} {dec}0s", combos=False)

    with open(os.path.join(HERE, "data", "powerball", "draws.csv"), newline="") as f:
        pb = list(csv.DictReader(f))
    red = [0] * 26
    white = [0] * 69
    for r in pb:
        red[int(r["red"]) - 1] += 1
        for i in range(1, 6):
            white[int(r[f"w{i}"]) - 1] += 1
    tests.append({"test": "powerball · red frequency", "counts": red, **gof(red)})
    tests.append({"test": "powerball · white frequency (without-replacement scaled)",
                  "counts": white, **gof(white, scale=(69 - 1) / (69 - 5))})

    alpha = 0.05 / len(tests)
    for t in tests:
        t["rejects_uniform_bonferroni"] = t["p"] < alpha
        t["below_0.05_uncorrected"] = t["p"] < 0.05
    failed = [t["test"] for t in tests if t["rejects_uniform_bonferroni"]]
    nominal = [t["test"] for t in tests if t["below_0.05_uncorrected"]]
    out = {
        "tests_run": len(tests),
        "bonferroni_alpha": alpha,
        "rejected_at_bonferroni": failed,
        "below_0.05_uncorrected": nominal,
        "expected_below_0.05_by_chance": round(0.05 * len(tests), 2),
        "pick3_draws": len(rows),
        "powerball_draws": len(pb),
        "tests": tests,
    }
    os.makedirs(os.path.join(HERE, "research"), exist_ok=True)
    with open(os.path.join(HERE, "research", "precheck.json"), "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    for t in tests:
        flag = "REJECT" if t["rejects_uniform_bonferroni"] else ("p<.05" if t["below_0.05_uncorrected"] else "")
        print(f"{t['test']:<62} chi2 {t['chi2']:>9.2f} df {t['df']:>3} p {t['p']:.4f} n {t['n']:>6} {flag}")
    print(f"\n{len(tests)} tests, Bonferroni alpha {alpha:.5f}: {len(failed)} rejected; "
          f"{len(nominal)} below 0.05 uncorrected ({out['expected_below_0.05_by_chance']} expected by chance)")


if __name__ == "__main__":
    main()
