"""crosscheck.py -- compare the two sources per game, then write the corpus.

Stage 2 of the lucky pipeline (fetch -> crosscheck -> prepare). Stdlib only.

Reads the per-source parses fetch.py left in data/raw/ and writes:

  data/pick3/draws.csv       date,draw,digits        (midday before evening)
  data/powerball/draws.csv   date,w1..w5,red         (whites sorted, as published)
  data/provenance.json       every source URL, the fetch date, the counts,
                             and every draw the two sources disagree on

The rule for the corpus: a draw is kept when the primary (official) source
has it. Where the second source disagrees or lacks the draw, the primary's
value stands and the draw is listed in provenance.json. Nothing is dropped
silently and nothing is repaired by hand.

Run from the repo root:
    uv run python projects/lucky/data/crosscheck.py
"""

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")

SOURCES = {
    "pick3": {
        "primary": {
            "name": "Maryland Lottery (mdlottery.com), winning-numbers search",
            "url": "https://www.mdlottery.com/player-tools/winning-numbers/",
            "endpoint": "https://www.mdlottery.com/wp-admin/admin-ajax.php"
                        "?action=jquery_shortcode&shortcode=find_numbers"
                        "&atts={\"game\":\"pick-3-4-5\",\"start\":\"01/01/<year>\",\"end\":\"12/31/<year>\",\"method\":\"ANY\"}",
            "requests": "one per year, 1976 to the fetch year",
        },
        "second": {
            "name": "LotteryCorner (lotterycorner.com), third-party archive",
            "url": "https://www.lotterycorner.com/md/pick-3-evening/<year> and "
                   "https://www.lotterycorner.com/md/pick-3-midday/<year>",
            "requests": "one per draw time per year (midday from 1995)",
        },
    },
    "powerball": {
        "primary": {
            "name": "New York open data, Lottery Powerball Winning Numbers: Beginning 2010",
            "url": "https://data.ny.gov/api/views/d6yy-54nr/rows.csv?accessType=DOWNLOAD",
        },
        "second": {
            "name": "Texas Lottery, Powerball past winning numbers (draw order)",
            "url": "https://www.texaslottery.com/export/sites/lottery/Games/Powerball/Winning_Numbers/powerball.csv",
        },
    },
}


def read(name):
    with open(os.path.join(RAW, name), newline="") as f:
        return list(csv.DictReader(f))


def compare(primary, second):
    """primary/second: {key: value}. Returns the disagreement record."""
    both = set(primary) & set(second)
    differ = sorted(k for k in both if primary[k] != second[k])
    return {
        "primary_draws": len(primary),
        "second_draws": len(second),
        "in_both_and_equal": len(both) - len(differ),
        "in_both_and_different": [
            {"draw": list(k) if isinstance(k, tuple) else k,
             "primary": primary[k], "second": second[k]} for k in differ],
        "only_in_primary": sorted(list(k) if isinstance(k, tuple) else k for k in set(primary) - set(second)),
        "only_in_second": [
            {"draw": list(k) if isinstance(k, tuple) else k, "second": second[k]}
            for k in sorted(set(second) - set(primary))],
    }


def main():
    with open(os.path.join(RAW, "fetch-log.json")) as f:
        fetched = json.load(f)
    prov = {"_note": "Written by projects/lucky/data/crosscheck.py. Draws come from "
                     "physical draw machines; no model wrote any of this corpus."}

    # --- Pick 3 ---------------------------------------------------------------
    order = {"midday": 0, "evening": 1}
    md = {(r["date"], r["draw"]): r["digits"] for r in read("pick3.mdlottery.csv")}
    lc = {(r["date"], r["draw"]): r["digits"] for r in read("pick3.lotterycorner.csv")}
    rows = sorted(md.items(), key=lambda kv: (kv[0][0], order[kv[0][1]]))
    os.makedirs(os.path.join(HERE, "pick3"), exist_ok=True)
    with open(os.path.join(HERE, "pick3", "draws.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "draw", "digits"])
        for (date, draw), digits in rows:
            w.writerow([date, draw, digits])
    by_time = {t: [k[0] for k, _ in rows if k[1] == t] for t in order}
    prov["pick3"] = {
        "game": "Maryland Pick 3",
        "fetched": fetched["pick3"]["fetched"],
        "sources": SOURCES["pick3"],
        "corpus": "projects/lucky/data/pick3/draws.csv",
        "draws": len(rows),
        "evening": {"draws": len(by_time["evening"]), "first": by_time["evening"][0], "last": by_time["evening"][-1]},
        "midday": {"draws": len(by_time["midday"]), "first": by_time["midday"][0], "last": by_time["midday"][-1]},
        "crosscheck": compare(md, lc),
    }

    # --- Powerball ------------------------------------------------------------
    def key(r):
        return [sorted(int(r[f"w{i}"]) for i in range(1, 6)), int(r["red"])]
    ny = {r["date"]: key(r) for r in read("powerball.ny.csv")}
    tx = {r["date"]: key(r) for r in read("powerball.texas.csv")}
    dates = sorted(ny)
    os.makedirs(os.path.join(HERE, "powerball"), exist_ok=True)
    with open(os.path.join(HERE, "powerball", "draws.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "w1", "w2", "w3", "w4", "w5", "red"])
        for d in dates:
            w.writerow([d, *ny[d][0], ny[d][1]])
    prov["powerball"] = {
        "game": "Powerball, 69/26 matrix (first draw 2015-10-07)",
        "fetched": fetched["powerball"]["fetched"],
        "sources": SOURCES["powerball"],
        "corpus": "projects/lucky/data/powerball/draws.csv",
        "draws": len(dates),
        "first": dates[0],
        "last": dates[-1],
        "note": "Whites are compared as sets: New York publishes them sorted, Texas in draw order. "
                "Power Play and Double Play are not in the corpus.",
        "crosscheck": compare(ny, tx),
    }

    with open(os.path.join(HERE, "provenance.json"), "w") as f:
        json.dump(prov, f, indent=2)
        f.write("\n")
    for g in ("pick3", "powerball"):
        c = prov[g]["crosscheck"]
        print(f"{g}: {prov[g]['draws']} draws; equal in both {c['in_both_and_equal']}, "
              f"different {len(c['in_both_and_different'])}, only primary {len(c['only_in_primary'])}, "
              f"only second {len(c['only_in_second'])}")


if __name__ == "__main__":
    main()
