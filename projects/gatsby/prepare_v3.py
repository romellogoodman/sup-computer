"""
Build the training sets for gatsby-nanogpt-3 from tiny-green-light-stories v3.

Reads data/v3/stories.jsonl (generate_v3.py) and writes three nested subsets of
the TRAIN split, chosen by topic so each topic keeps all five of its levels (the
dial's contrast lives inside a topic):

    data/gatsby_v3_5k/     1,000 train topics   ->  5,000 stories
    data/gatsby_v3_10k/    2,000 train topics   -> 10,000 stories
    data/gatsby_v3_full/   every train topic    -> the whole train split

All three share ONE byte-level BPE tokenizer (1024 vocab, trained on the full
train split only) and ONE val.bin built from the val split's topics, so the
three runs' val losses are directly comparable. The test split's topics are
never seen in training; eval_v3.py scores on them.

Each document is formatted exactly as every gatsby corpus is:
generate.py:build_prime(topic, level) + story + blank line.

The subset specs (seeded topic-id lists) are written to data/v3/subsets/ so
the Hugging Face dataset can declare exactly what gatsby-nanogpt-3 trained on.

Run from the repo root:
    uv run python projects/gatsby/prepare_v3.py
"""
import json
import os
import pickle
import random
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from generate import format_doc  # noqa: E402  (build_prime + story + "\n\n")
from prepare import VOCAB_SIZE, train_tokenizer  # noqa: E402

V3 = os.path.join(HERE, "data", "v3")
SEED = 1925
SUBSETS = {"5k": 1000, "10k": 2000, "full": None}   # name -> number of train topics


def docs_text(rows, rng):
    rows = rows[:]
    rng.shuffle(rows)   # interleave topics and levels
    return "".join(format_doc(r["topic"], r["level"], r["text"]) for r in rows)


def write_bins(tok, out_dir, train_text, val_ids):
    os.makedirs(out_dir, exist_ok=True)
    ids = tok.encode(train_text).ids
    assert max(ids) < 65535, "ids exceed uint16"
    np.array(ids, dtype=np.uint16).tofile(os.path.join(out_dir, "train.bin"))
    np.array(val_ids, dtype=np.uint16).tofile(os.path.join(out_dir, "val.bin"))
    with open(os.path.join(out_dir, "meta.pkl"), "wb") as f:
        pickle.dump({"vocab_size": tok.get_vocab_size(), "tokenizer": "tokenizer.json"}, f)
    return len(ids)


def main():
    rows = [json.loads(line) for line in open(os.path.join(V3, "stories.jsonl"), encoding="utf-8")]
    by_split = {s: [r for r in rows if r["split"] == s] for s in ("train", "val", "test")}
    train_topics = sorted({r["topic_id"] for r in by_split["train"]})
    random.Random(SEED).shuffle(train_topics)   # nested: 5k ⊂ 10k ⊂ full

    full_train_text = docs_text(by_split["train"], random.Random(SEED))
    val_text = docs_text(by_split["val"], random.Random(SEED))
    tok_dir = os.path.join(HERE, "data", "gatsby_v3_full")
    os.makedirs(tok_dir, exist_ok=True)
    tok_path = os.path.join(tok_dir, "tokenizer.json")
    tok = train_tokenizer(full_train_text, VOCAB_SIZE, tok_path)
    val_ids = tok.encode(val_text).ids

    sub_dir = os.path.join(V3, "subsets")
    os.makedirs(sub_dir, exist_ok=True)
    report = {}
    for name, n_topics in SUBSETS.items():
        keep = set(train_topics if n_topics is None else train_topics[:n_topics])
        sub_rows = [r for r in by_split["train"] if r["topic_id"] in keep]
        out_dir = os.path.join(HERE, "data", f"gatsby_v3_{name}")
        os.makedirs(out_dir, exist_ok=True)
        if out_dir != tok_dir:
            shutil.copy(tok_path, os.path.join(out_dir, "tokenizer.json"))
        text = full_train_text if n_topics is None else docs_text(sub_rows, random.Random(SEED))
        n_tok = write_bins(tok, out_dir, text, val_ids)
        json.dump({"name": f"train-{name}", "seed": SEED, "split": "train",
                   "topics": len(keep), "stories": len(sub_rows),
                   "rule": "seeded shuffle of train topic ids; first N topics, all five levels each "
                           "(nested: 5k ⊂ 10k ⊂ full)",
                   "topic_ids": sorted(keep)},
                  open(os.path.join(sub_dir, f"train-{name}.json"), "w"), indent=1)
        report[name] = {"topics": len(keep), "stories": len(sub_rows),
                        "chars": len(text), "tokens": n_tok}
        print(f"gatsby_v3_{name}: {len(keep):,} topics, {len(sub_rows):,} stories, "
              f"{len(text):,} chars -> {n_tok:,} tokens")
    report["val"] = {"stories": len(by_split["val"]), "tokens": len(val_ids)}
    report["test"] = {"stories": len(by_split["test"])}
    report["vocab_size"] = tok.get_vocab_size()
    json.dump(report, open(os.path.join(V3, "prepare-stats.json"), "w"), indent=1)
    print(f"val: {len(by_split['val']):,} stories -> {len(val_ids):,} tokens; "
          f"test: {len(by_split['test']):,} stories (held out)")


if __name__ == "__main__":
    main()
