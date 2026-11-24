"""test_score_sheets.py — score_sheets.py against synthetic ratings with known answers.

No model and no real ratings: builds a sheet and key in a temp dir, fills
them by rule, and checks the tables, P2, P3 and the error path.

    uv run python projects/oblique/test_score_sheets.py
"""
import csv
import os
import tempfile

import score_sheets as ss

TEMPS = [0.6, 0.8, 1.0, 1.2, 1.4]
# keepers out of 20 per temperature, by register
PLAN = {"s": [2, 6, 10, 4, 1], "f": [0, 1, 1, 0, 0]}


def write(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def build(tmp, plan=PLAN, blank=None, shuffle_stride=7):
    key, sheet = [], []
    i = 0
    for reg, counts in plan.items():
        for temp, keepers in zip(TEMPS, counts):
            for j in range(20):
                i += 1
                rid = f"D{i:03d}"
                keep = j < keepers
                # a keeper is 4/5 or 5/4; a non-keeper misses on one axis
                strange = (4 if j % 2 else 5) if keep else (5 if reg == "s" else 2)
                usable = (5 if j % 2 else 4) if keep else (2 if reg == "s" else 3)
                key.append([rid, reg, temp, "none", "t", 1, 1, 0, 1, "", reg, "x"])
                sheet.append([rid, "a line", "" if rid == blank else strange, usable])
    # the sheet's order is not the key's order
    sheet = sheet[::shuffle_stride] + [r for k, r in enumerate(sheet) if k % shuffle_stride]
    header = ["id", "register", "temperature", "soft_cap", "run", "step", "sample_seed",
              "in_training_set", "wellformed", "malformed", "classifier_guess", "raw_line"]
    write(os.path.join(tmp, "KEY-dial.csv"), header, key)
    write(os.path.join(tmp, "dial.csv"), ["id", "line", "strange", "usable"], sheet)

    rkey, rsheet = [], []
    for n in range(60):
        reg = "s" if n < 30 else "f"
        clf = reg if n % 10 else ("f" if reg == "s" else "s")      # classifier right 54/60
        guess = reg if n % 5 else ("f" if reg == "s" else "s")     # rater right 48/60
        rkey.append([f"R{n + 1:03d}", reg, 1.0, "none", "t", 1, 1, 0, 1, "", clf, "x"])
        rsheet.append([f"R{n + 1:03d}", "a line", ["s", "F", "Strategy", "fortune"][
            (0 if guess == "s" else 1) + (2 if n % 2 else 0)]])
    write(os.path.join(tmp, "KEY-register.csv"), header, rkey)
    write(os.path.join(tmp, "register.csv"), ["id", "line", "guess"], rsheet)
    return [os.path.join(tmp, n) for n in
            ("dial.csv", "KEY-dial.csv", "register.csv", "KEY-register.csv")]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        result, problems = ss.score(*build(tmp))
        assert not problems, problems
        got = {(r["register"], r["temperature"]): r for r in result["dial"]}
        for reg, counts in PLAN.items():
            for temp, keepers in zip(TEMPS, counts):
                row = got[(reg, temp)]
                assert row["n"] == 20 and row["keepers"] == keepers, row
                assert abs(row["keeper_rate"] - keepers / 20) < 1e-9
        # s at 1.0: ten keepers averaging 4.5 strange, ten non-keepers at 5
        assert abs(got[("s", 1.0)]["mean_strange"] - 4.75) < 1e-9
        assert abs(got[("s", 1.0)]["mean_usable"] - 3.25) < 1e-9
        p2 = result["p2"]
        assert p2["holds"] and p2["peak_temperatures"] == [1.0], p2
        assert p2["peak_keeper_rate"] == 0.5 and p2["lowest_setting_rate"] == 0.1
        assert result["p3"]["holds"], result["p3"]
        reg = result["register"]
        assert reg["n"] == 60
        assert abs(reg["rater_agrees_with_token"] - 48 / 60) < 1e-9, reg
        assert abs(reg["classifier_agrees_with_token"] - 54 / 60) < 1e-9, reg
        # they agree where both are right (48) and where both are wrong (6)
        assert abs(reg["rater_agrees_with_classifier"] - 54 / 60) < 1e-9, reg
        assert ss.markdown(result).count("\n") > 10

    # P2 must be able to fail: a flat curve, a peak at the hot end, a peak under 2x
    for plan, why in (
            ({"s": [3, 3, 3, 3, 3], "f": [0] * 5}, "flat"),
            ({"s": [1, 2, 4, 6, 9], "f": [0] * 5}, "peak at an end"),
            ({"s": [4, 5, 6, 5, 4], "f": [0] * 5}, "under twice the ends"),
            ({"s": [0, 0, 0, 0, 0], "f": [0] * 5}, "no keepers at all"),
            ({"s": [1, 2, 3, 9, 1], "f": [0] * 5}, "peak at 1.2 is inside the band")):
        with tempfile.TemporaryDirectory() as tmp:
            result, problems = ss.score(*build(tmp, plan=plan))
            assert not problems
            expect = why == "peak at 1.2 is inside the band"
            assert result["p2"]["holds"] is expect, (why, result["p2"])

    # P3 must be able to fail: strategies rated more usable than fortunes when cold
    with tempfile.TemporaryDirectory() as tmp:
        result, _ = ss.score(*build(tmp, plan={"s": [20] * 5, "f": [0] * 5}))
        p3 = result["p3"]
        assert p3["fortunes_less_strange_everywhere"] and not p3["fortunes_more_usable_at_lowest"]
        assert not p3["holds"], p3

    # a blank rating is an error naming the row
    with tempfile.TemporaryDirectory() as tmp:
        _, problems = ss.score(*build(tmp, blank="D017"))
        assert problems == ["D017: strange is blank"], problems

    print("ok: tables, P2 (holds and four ways to fail), P3, register agreement, blank-cell error")


if __name__ == "__main__":
    main()
