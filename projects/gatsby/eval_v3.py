"""
Score a gatsby-nanogpt-3 sweep run on the v3 TEST split — topics no run trained on.

Two numbers per run, both on the same held-out topics:

- dial: green mentions per level, counted in the first 480 characters of the
  continuation (the yardstick eval_dial.py and gatsby-nanogpt-2 use).
- topic-honoring: share of continuations whose first 480 characters contain a
  content word of the topic (4-letter stem match). A crude proxy, but the same
  proxy for every run and for the reference row.

The reference row scores the test split's own stories (what the corpus does),
so a run can be read against the ceiling its data sets.

Run from the repo root:
    uv run python projects/gatsby/eval_v3.py --runs v3-5k v3-10k v3-full
Writes runs/v3-eval.json.
"""
import argparse
import json
import os
import random
import re
import statistics as st

from _runtime import generate, load_model_and_tokenizer, pick_device
from generate import build_prime

HERE = os.path.dirname(os.path.abspath(__file__))
STOP = set("a an the and of with in on at to for his her their my is that who what from "
           "into very small little big tiny".split())


def stems(topic):
    return {w[:4] for w in re.findall(r"[a-z]+", topic.lower()) if w not in STOP and len(w) > 2}


def honors(text, topic):
    words = {w[:4] for w in re.findall(r"[a-z]+", text.lower())}
    return bool(stems(topic) & words)


def greens(text):
    return len(re.findall(r"green", text, re.I))


def summarize(items):
    dial = [round(st.mean(greens(t) for lv, t, _ in items if lv == level), 2) for level in range(1, 6)]
    hon = sum(honors(t, topic) for _, t, topic in items) / len(items)
    return {"dial": dial, "topic_honoring": round(hon, 3), "n": len(items)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--topics", type=int, default=30)
    ap.add_argument("--chars", type=int, default=480)
    ap.add_argument("--gen_tokens", type=int, default=220)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    bank = json.load(open(os.path.join(HERE, "data", "v3", "topics.json")))
    test = [t for t in bank["topics"] if t["split"] == "test"]
    test = random.Random(args.seed).sample(test, min(args.topics, len(test)))
    ids = {t["topic_id"] for t in test}

    rows = [json.loads(line) for line in open(os.path.join(HERE, "data", "v3", "stories.jsonl"))]
    ref = [(r["level"], r["text"][: args.chars], r["topic"]) for r in rows if r["topic_id"] in ids]
    out = {"test_topics": [t["topic"] for t in test], "reference_corpus": summarize(ref)}
    print(f"reference (test-split stories): {out['reference_corpus']}")

    device = pick_device(args.device)
    data_dir = os.path.join(HERE, "data")
    for run in args.runs:
        run_dir = os.path.join(HERE, "runs", run)
        if not os.path.exists(os.path.join(run_dir, "ckpt.pt")):
            print(f"{run}: no checkpoint, skipped")
            continue
        model, tok = load_model_and_tokenizer(run_dir, data_dir, device)
        items, samples = [], {}
        for i, t in enumerate(test):
            for level in range(1, 6):
                prime = build_prime(t["topic"], level)
                full = generate(model, tok, prime, args.gen_tokens, device, seed=1000 + i)
                cont = full[len(prime):][: args.chars]
                items.append((level, cont, t["topic"]))
                if i == 0:
                    samples[level] = cont
        out[run] = {**summarize(items), "samples_first_topic": samples}
        print(f"{run}: dial {out[run]['dial']}  topic-honoring {out[run]['topic_honoring']:.0%}")
    json.dump(out, open(os.path.join(HERE, "runs", "v3-eval.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
