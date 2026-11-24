"""score_sheets.py — filled rating sheets plus their keys in, the tables out.

Dial sheet: per temperature and register, the keeper rate (strange >= 4 and
usable >= 4) with the two mean ratings, then P2 and P3 read off the table.
Register sheet: how often the rater's guess matches the token that produced
the line, how often it matches the corpus-trained classifier, and how often
the classifier matches the token on the same 60 lines.

Second-seed sheet, once it exists and is filled: the same table for the
second seed's three temperatures, where its [s] keeper rate peaks, and
whether that peak lands within 0.2 of the first seed's (the last clause of
P2).

A blank or out-of-range rating is an error naming the row, not a zero.

Run from the repo root, after filling the two sheets in place:
    uv run python projects/oblique/score_sheets.py

or name the files:
    uv run python projects/oblique/score_sheets.py \\
        --dial path/to/dial-sheet.csv --dial-key path/to/KEY-dial.csv \\
        --register path/to/register-sheet.csv --register-key path/to/KEY-register.csv
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SHEETS = os.path.join(HERE, "research", "sheets")
KEEPER = 4


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def join(sheet_path, key_path, fields):
    """Sheet rows joined to key rows by id. Every id must appear in both,
    once, and every field in `fields` must be filled."""
    sheet, key = read_csv(sheet_path), {r["id"]: r for r in read_csv(key_path)}
    seen, rows, problems = set(), [], []
    for r in sheet:
        rid = (r.get("id") or "").strip()
        if rid in seen:
            problems.append(f"{rid}: appears twice in the sheet")
        seen.add(rid)
        if rid not in key:
            problems.append(f"{rid!r}: not in the key")
            continue
        row = {**key[rid]}
        for name in fields:
            row[name] = (r.get(name) or "").strip()
            if not row[name]:
                problems.append(f"{rid}: {name} is blank")
        rows.append(row)
    for rid in key:
        if rid not in seen:
            problems.append(f"{rid}: in the key, missing from the sheet")
    return rows, problems


def rating(row, name, problems):
    try:
        v = int(float(row[name]))
    except ValueError:
        if row[name]:
            problems.append(f"{row['id']}: {name} is {row[name]!r}, not a number")
        return None
    if not 1 <= v <= 5:
        problems.append(f"{row['id']}: {name} is {v}, outside 1-5")
        return None
    return v


def score_dial(rows, problems):
    cells = defaultdict(list)
    for r in rows:
        s, u = rating(r, "strange", problems), rating(r, "usable", problems)
        if s is not None and u is not None:
            cells[(r["register"], float(r["temperature"]))].append((s, u, r))
    table = []
    for (reg, temp), vals in sorted(cells.items()):
        n = len(vals)
        keepers = [v for v in vals if v[0] >= KEEPER and v[1] >= KEEPER]
        table.append({
            "register": reg, "temperature": temp, "n": n,
            "keepers": len(keepers), "keeper_rate": len(keepers) / n,
            "mean_strange": sum(v[0] for v in vals) / n,
            "mean_usable": sum(v[1] for v in vals) / n,
            "keepers_copied_from_training": sum(int(v[2].get("in_training_set", 0) or 0)
                                                for v in keepers),
        })
    return table


def read_p2(table):
    """P2 on the [s] rows: an interior peak at least twice both end values,
    sitting between 0.8 and 1.2."""
    s = sorted((r for r in table if r["register"] == "s"), key=lambda r: r["temperature"])
    if len(s) < 3:
        return {"scored": False, "why": "fewer than three temperatures"}
    rates = [r["keeper_rate"] for r in s]
    top = max(rates)
    peaks = [r["temperature"] for r in s if r["keeper_rate"] == top]
    low, high = rates[0], rates[-1]
    interior = top > 0 and all(s[0]["temperature"] < p < s[-1]["temperature"] for p in peaks)
    twice = top > 0 and top >= 2 * low and top >= 2 * high
    in_band = all(0.8 <= p <= 1.2 for p in peaks)
    return {"scored": True, "peak_keeper_rate": top, "peak_temperatures": peaks,
            "lowest_setting_rate": low, "highest_setting_rate": high,
            "interior_peak": interior, "at_least_twice_both_ends": twice,
            "peak_between_0.8_and_1.2": in_band,
            "holds": bool(interior and twice and in_band),
            "second_seed_check": "pending: the second seed's peak must land within 0.2"}


def read_p3(table):
    """P3: [f] below [s] on strange at every temperature, and [f] above [s]
    on usable at the lowest temperature."""
    by = {(r["register"], r["temperature"]): r for r in table}
    temps = sorted({t for _, t in by})
    rows = []
    for t in temps:
        if ("s", t) in by and ("f", t) in by:
            rows.append({"temperature": t,
                         "strange_s": by[("s", t)]["mean_strange"],
                         "strange_f": by[("f", t)]["mean_strange"],
                         "usable_s": by[("s", t)]["mean_usable"],
                         "usable_f": by[("f", t)]["mean_usable"]})
    if not rows:
        return {"scored": False, "why": "no temperature has both registers"}
    floor = all(r["strange_f"] < r["strange_s"] for r in rows)
    usable_low = rows[0]["usable_f"] > rows[0]["usable_s"]
    return {"scored": True, "by_temperature": rows,
            "fortunes_less_strange_everywhere": floor,
            "fortunes_more_usable_at_lowest": usable_low,
            "holds": bool(floor and usable_low)}


def read_second_seed(first, second):
    """Where each seed's [s] keeper rate peaks, and whether the second lands
    within 0.2 of the first. A temperature only one seed was rated at is
    listed, because there seed and temperature can't be told apart."""
    def s_rows(table):
        return sorted((r for r in table if r["register"] == "s"),
                      key=lambda r: r["temperature"])

    def peaks(rows):
        top = max(r["keeper_rate"] for r in rows)
        return top, [r["temperature"] for r in rows if r["keeper_rate"] == top]

    a, b = s_rows(first), s_rows(second)
    if not a or not b:
        return {"scored": False, "why": "a seed has no [s] rows"}
    top_a, peaks_a = peaks(a)
    top_b, peaks_b = peaks(b)
    within = top_b > 0 and any(abs(x - y) <= 0.2 + 1e-9 for x in peaks_a for y in peaks_b)
    first_by = {r["temperature"]: r for r in a}
    shared = [{"temperature": r["temperature"],
               "first_seed_keeper_rate": first_by[r["temperature"]]["keeper_rate"],
               "second_seed_keeper_rate": r["keeper_rate"]}
              for r in b if r["temperature"] in first_by]
    return {"scored": True,
            "first_seed_peak_rate": top_a, "first_seed_peak_temperatures": peaks_a,
            "second_seed_peak_rate": top_b, "second_seed_peak_temperatures": peaks_b,
            "second_peak_within_0.2_of_first": bool(within),
            "shared_temperatures": shared,
            "temperatures_only_second_seed_was_rated_at":
                [r["temperature"] for r in b if r["temperature"] not in first_by]}


def score_register(rows, problems):
    alias = {"s": "s", "strategy": "s", "[s]": "s", "f": "f", "fortune": "f", "[f]": "f"}
    n = token = clf = clf_token = 0
    confusion = defaultdict(int)
    for r in rows:
        g = alias.get(r["guess"].lower())
        if g is None:
            if r["guess"]:
                problems.append(f"{r['id']}: guess is {r['guess']!r}, expected s or f")
            continue
        n += 1
        token += g == r["register"]
        clf += g == r["classifier_guess"]
        clf_token += r["classifier_guess"] == r["register"]
        confusion[f"token {r['register']} / guessed {g}"] += 1
    if not n:
        return {"scored": False}
    return {"scored": True, "n": n,
            "rater_agrees_with_token": token / n,
            "rater_agrees_with_classifier": clf / n,
            "classifier_agrees_with_token": clf_token / n,
            "confusion": dict(sorted(confusion.items()))}


def markdown(result):
    out = []
    if result.get("dial"):
        out += ["| register | temperature | n | keepers | keeper rate | mean strange | mean usable |",
                "|---|---|---|---|---|---|---|"]
        for r in result["dial"]:
            out.append(f"| {r['register']} | {r['temperature']:g} | {r['n']} | {r['keepers']} | "
                       f"{r['keeper_rate']:.0%} | {r['mean_strange']:.2f} | {r['mean_usable']:.2f} |")
        p2, p3 = result["p2"], result["p3"]
        if p2["scored"]:
            out.append(f"\nP2 {'holds' if p2['holds'] else 'fails'} on this seed: peak "
                       f"{p2['peak_keeper_rate']:.0%} at {p2['peak_temperatures']}, ends "
                       f"{p2['lowest_setting_rate']:.0%} and {p2['highest_setting_rate']:.0%}.")
        if p3["scored"]:
            out.append(f"P3 {'holds' if p3['holds'] else 'fails'}: fortunes less strange at every "
                       f"temperature {p3['fortunes_less_strange_everywhere']}, more usable at the "
                       f"lowest {p3['fortunes_more_usable_at_lowest']}.")
    if result.get("seed2"):
        out += ["\nSecond seed:\n",
                "| register | temperature | n | keepers | keeper rate | mean strange | mean usable |",
                "|---|---|---|---|---|---|---|"]
        for r in result["seed2"]:
            out.append(f"| {r['register']} | {r['temperature']:g} | {r['n']} | {r['keepers']} | "
                       f"{r['keeper_rate']:.0%} | {r['mean_strange']:.2f} | {r['mean_usable']:.2f} |")
        ss = result.get("second_seed")
        if ss and ss["scored"]:
            out.append(f"\nSecond seed's [s] peak: {ss['second_seed_peak_rate']:.0%} at "
                       f"{ss['second_seed_peak_temperatures']}; first seed's: "
                       f"{ss['first_seed_peak_rate']:.0%} at {ss['first_seed_peak_temperatures']}. "
                       f"Within 0.2: {ss['second_peak_within_0.2_of_first']}.")
            if ss["temperatures_only_second_seed_was_rated_at"]:
                out.append(f"Only the second seed was rated at "
                           f"{ss['temperatures_only_second_seed_was_rated_at']}: seed and "
                           f"temperature are confounded there.")
    reg = result.get("register")
    if reg and reg["scored"]:
        out.append(f"\nRegister test, {reg['n']} lines: rater agrees with the token "
                   f"{reg['rater_agrees_with_token']:.0%}, with the classifier "
                   f"{reg['rater_agrees_with_classifier']:.0%}; the classifier agrees with the "
                   f"token {reg['classifier_agrees_with_token']:.0%}.")
    return "\n".join(out)


def score(dial=None, dial_key=None, register=None, register_key=None,
          seed2=None, seed2_key=None):
    result, problems = {}, []
    if dial:
        rows, p = join(dial, dial_key, ["strange", "usable"])
        problems += p
        result["dial"] = score_dial(rows, problems)
        result["p2"] = read_p2(result["dial"])
        result["p3"] = read_p3(result["dial"])
    if register:
        rows, p = join(register, register_key, ["guess"])
        problems += p
        result["register"] = score_register(rows, problems)
    if seed2:
        rows, p = join(seed2, seed2_key, ["strange", "usable"])
        problems += p
        result["seed2"] = score_dial(rows, problems)
        if result.get("dial"):
            result["second_seed"] = read_second_seed(result["dial"], result["seed2"])
            if result["second_seed"]["scored"]:
                result["p2"]["second_seed_check"] = (
                    "within 0.2 of the first seed's peak"
                    if result["second_seed"]["second_peak_within_0.2_of_first"]
                    else "not within 0.2 of the first seed's peak")
    return result, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dial", default=os.path.join(SHEETS, "dial-sheet.csv"))
    ap.add_argument("--dial-key", default=os.path.join(SHEETS, "KEY-dial.csv"))
    ap.add_argument("--register", default=os.path.join(SHEETS, "register-sheet.csv"))
    ap.add_argument("--register-key", default=os.path.join(SHEETS, "KEY-register.csv"))
    ap.add_argument("--seed2", default=os.path.join(SHEETS, "seed2-sheet.csv"))
    ap.add_argument("--seed2-key", default=os.path.join(SHEETS, "KEY-seed2.csv"))
    ap.add_argument("--skip-seed2", action="store_true",
                    help="leave the second-seed sheet out (it is also left out "
                         "when the file does not exist)")
    ap.add_argument("--skip-dial", action="store_true")
    ap.add_argument("--skip-register", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "research", "ratings-scored.json"))
    args = ap.parse_args()

    seed2 = None if args.skip_seed2 or not os.path.exists(args.seed2) else args.seed2
    result, problems = score(
        None if args.skip_dial else args.dial, args.dial_key,
        None if args.skip_register else args.register, args.register_key,
        seed2, args.seed2_key)
    if problems:
        print(f"{len(problems)} problems; nothing scored:", file=sys.stderr)
        for p in problems[:40]:
            print("  " + p, file=sys.stderr)
        sys.exit(1)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=1)
        f.write("\n")
    print(markdown(result))
    print(f"\nwrote {os.path.relpath(args.out)}")


if __name__ == "__main__":
    main()
