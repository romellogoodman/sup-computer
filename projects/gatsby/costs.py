"""
Summarise the cost of generating the Gatsby corpus.

generate.py appends a record per run to data/costs.jsonl (token usage + dollar
cost). This prints those records as a table and totals them -- the real-money
cost of building this model's training data, tracked like the Shakespeare
project tracked its researcher cost.

Usage:
  python costs.py
"""
import os
import json

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "data", "costs.jsonl")


def main():
    if not os.path.exists(LOG):
        raise SystemExit("No data/costs.jsonl yet -- run generate.py first.")

    rows = []
    with open(LOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    print(f"{'when (UTC)':<20} {'stories':>8} {'chars':>10} "
          f"{'out tok':>10} {'mode':>6} {'cost $':>9}")
    print("-" * 70)
    total_cost = total_stories = total_chars = total_out = 0
    for r in rows:
        out_tok = r["topic_usage"]["output"] + r["story_usage"]["output"]
        mode = "batch" if r.get("batch") else "sync"
        when = r["timestamp"][:19].replace("T", " ")
        print(f"{when:<20} {r['n_stories']:>8,} {r['corpus_chars']:>10,} "
              f"{out_tok:>10,} {mode:>6} {r['cost_usd']:>9.4f}")
        total_cost += r["cost_usd"]
        total_stories += r["n_stories"]
        total_chars += r["corpus_chars"]
        total_out += out_tok
    print("-" * 70)
    print(f"{'TOTAL':<20} {total_stories:>8,} {total_chars:>10,} "
          f"{total_out:>10,} {'':>6} {total_cost:>9.4f}")


if __name__ == "__main__":
    main()
