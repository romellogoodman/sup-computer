"""
Rebuild gatsby-nanogpt-3's training data in place, from the published dataset.

The corpus was written by an LLM, so it cannot regenerate deterministically; its
record is the Hugging Face dataset sup-computer/tiny-green-light-stories at tag
v3. This script downloads that revision, keeps the training subset named in
config.py (`subset`), formats each story with the gatsby control line, and
encodes it with the PINNED tokenizer.json (never retrained here).

    python prepare.py      # -> data/{train,val}.bin + data/meta.pkl

Needs `huggingface_hub` and `tokenizers`.
"""
import json
import os
import pickle
import random

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO, REVISION = "sup-computer/tiny-green-light-stories", "v3"
SEED = 1925
LEVEL_WORDS = {1: "faint", 2: "soft", 3: "strong", 4: "heavy", 5: "total"}


def build_prime(topic, level):
    """The control line — a verbatim copy of projects/gatsby/generate.py:build_prime."""
    word = LEVEL_WORDS.get(level, "total")
    tag = f"[green={level}]"
    return f"{tag} {tag} {tag} obsession={word}\ntopic: {topic}\n"


def docs_text(rows):
    rows = rows[:]
    random.Random(SEED).shuffle(rows)
    return "".join(f"{build_prime(r['topic'], r['level'])}{r['text']}\n\n" for r in rows)


def main():
    from huggingface_hub import hf_hub_download
    from tokenizers import Tokenizer

    cfg = {}
    exec(open(os.path.join(HERE, "config.py")).read(), cfg)
    get = lambda p: hf_hub_download(REPO, p, repo_type="dataset", revision=REVISION)  # noqa: E731
    read = lambda p: [json.loads(x) for x in open(get(p), encoding="utf-8")]  # noqa: E731
    subset = json.load(open(get(f"v3/subsets/{cfg['subset']}.json")))
    keep = set(subset["topic_ids"])
    train = [r for r in read("v3/train.jsonl") if r["topic_id"] in keep]
    val = read("v3/validation.jsonl")

    tok = Tokenizer.from_file(os.path.join(HERE, "data", "tokenizer.json"))
    out = os.path.join(HERE, "data")
    for name, rows in (("train", train), ("val", val)):
        ids = tok.encode(docs_text(rows)).ids
        np.array(ids, dtype=np.uint16).tofile(os.path.join(out, f"{name}.bin"))
        print(f"{name}: {len(rows):,} stories -> {len(ids):,} tokens")
    with open(os.path.join(out, "meta.pkl"), "wb") as f:
        pickle.dump({"vocab_size": tok.get_vocab_size(), "tokenizer": "tokenizer.json"}, f)


if __name__ == "__main__":
    main()
