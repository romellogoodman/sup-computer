"""score_corpus.py -- the pre-registered check that runs before any training:
score the corpus itself under the oracle.

Every parser is one snapshot of a drifting language; if the corpus scores 85%,
a model at 83% is near-ceiling, and the report must say so. This writes the
corpus-relative denominator (overall and per source) plus the corpus's own
error taxonomy to research/corpus_baseline.json.

Run from the repo root (after build_corpus.py and fetch_oracle.py):
    uv run python projects/pona/research/score_corpus.py --n 20000
"""
import argparse
import json
import os
import random
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJ, "oracle"))
from oracle import check_sentences  # noqa: E402

SENT_SPLIT = re.compile(r"(?<=[.!?])[\"')]*\s+")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000, help="sentences to sample")
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    corpus_path = os.path.join(PROJ, "data", "corpus", "natural.txt")
    sources_path = os.path.join(PROJ, "data", "corpus", "natural.sources.txt")
    with open(corpus_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    with open(sources_path, encoding="utf-8") as f:
        sources = f.read().splitlines()

    sentences = []  # (source, sentence)
    for line, src in zip(lines, sources):
        for s in SENT_SPLIT.split(line):
            s = s.strip()
            if len(s) >= 3:
                sentences.append((src, s))
    print(f"{len(sentences):,} sentences in corpus")

    rng = random.Random(args.seed)
    sample = rng.sample(sentences, min(args.n, len(sentences)))
    results = check_sentences([s for _, s in sample])

    def rates(pairs):
        n = len(pairs)
        hard_ok = sum(1 for _, r in pairs if not any(e["category"] == "error" for e in r["errors"]))
        strict_ok = sum(1 for _, r in pairs if not r["errors"])
        return {"n": n, "pass_rate_error_only": hard_ok / n, "pass_rate_strict": strict_ok / n}

    paired = list(zip([src for src, _ in sample], results))
    by_source = {}
    for src in sorted(set(s for s, _ in paired)):
        by_source[src] = rates([(s, r) for s, r in paired if s == src])

    taxonomy = Counter()
    for r in results:
        for e in r["errors"]:
            taxonomy[f"{e['category']}:{e['rule']}"] += 1

    mean_len = sum(len(s) for _, s in sample) / len(sample)
    out = {
        "sample_n": len(sample),
        "seed": args.seed,
        "corpus_sentences_total": len(sentences),
        "mean_sentence_chars": mean_len,
        "overall": rates(paired),
        "by_source": by_source,
        "error_taxonomy_top": dict(taxonomy.most_common(25)),
        "note": "pass_rate_error_only is the pre-registered denominator for "
                "corpus-relative grammaticality; strict counts possible-error too",
    }
    out_path = os.path.join(HERE, "corpus_baseline.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != "error_taxonomy_top"}, indent=2))
    print("top errors:", dict(taxonomy.most_common(8)))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
