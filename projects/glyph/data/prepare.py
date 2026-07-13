"""
prepare.py -- corpus text -> datasets for every arm.

Reads data/corpus/<letter>.txt (from encode_corpus.py), then:

  dedup      exact duplicate encoded lines per letter (google/fonts is full
             of forks) -- first occurrence wins, drops counted
  split      BY FAMILY, never by glyph: md5(family_dir) % 10 -> 0-7 train,
             8 val, 9 test. One assignment shared by every letter and every
             arm, so held-out families are unseen everywhere and
             specialist-vs-omni BPC is apples-to-apples.
  overlong   lines that don't fit block_size 512 (glyph + newline) dropped
             and counted
  datasets   data/<letter>/{train,val}.bin + meta.pkl   (26 specialists)
             data/omni/{train,val}.bin + meta.pkl       (union, shuffled)
  test       ../test/<letter>.txt -- committed, raw lines for the held-out
             families; eval.py scores every arm against these
  baseline   per-letter unigram BPC (train char frequencies, Laplace
             smoothing over the fixed alphabet, scored on the test file) ->
             ../research/baselines.json. Every model must clearly beat this
             or its number is noise.

The vocab is the codec's fixed 127-char alphabet for every dataset -- never
set(data) -- so all arms share one meta.pkl shape (ADR-0027).

Run from the repo root:
    uv run python projects/glyph/data/prepare.py
"""
import hashlib
import json
import math
import os
import pickle
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codec  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.join(HERE, "corpus")
TEST_DIR = os.path.normpath(os.path.join(HERE, "..", "test"))
RESEARCH_DIR = os.path.normpath(os.path.join(HERE, "..", "research"))
BLOCK_SIZE = 512
SEED = 1337

STOI, _ = codec.stoi_itos()
META = {"vocab_size": len(codec.ALPHABET), "stoi": STOI, "itos": {i: ch for ch, i in STOI.items()}}


def split_of(family_dir):
    h = int(hashlib.md5(family_dir.encode()).hexdigest(), 16) % 10
    return "train" if h < 8 else ("val" if h == 8 else "test")


def encode(text):
    return np.array([STOI[c] for c in text], dtype=np.uint16)


def write_dataset(name, train_lines, val_lines):
    out = os.path.join(HERE, name)
    os.makedirs(out, exist_ok=True)
    for split, lines in (("train", train_lines), ("val", val_lines)):
        text = "".join(line + "\n" for line in lines)
        encode(text).tofile(os.path.join(out, f"{split}.bin"))
    with open(os.path.join(out, "meta.pkl"), "wb") as f:
        pickle.dump(META, f)
    return sum(len(l) + 1 for l in train_lines), sum(len(l) + 1 for l in val_lines)


def unigram_bpc(train_lines, test_lines):
    """BPC of the smoothed train unigram distribution on the test text."""
    counts = {ch: 1 for ch in codec.ALPHABET}  # Laplace
    train_text = "".join(l + "\n" for l in train_lines)
    for ch in train_text:
        counts[ch] += 1
    total = sum(counts.values())
    logp = {ch: math.log2(c / total) for ch, c in counts.items()}
    test_text = "".join(l + "\n" for l in test_lines)
    return -sum(logp[ch] for ch in test_text) / len(test_text)


def main():
    rng = random.Random(SEED)
    os.makedirs(TEST_DIR, exist_ok=True)
    stats = {"per_letter": {}, "dropped_duplicates": 0, "dropped_overlong": 0}
    baselines = {}
    omni = {"train": [], "val": []}

    for letter in codec.LETTERS:
        seen, splits = set(), {"train": [], "val": [], "test": []}
        with open(os.path.join(CORPUS_DIR, f"{letter}.txt")) as f:
            for row in f:
                family_dir, _, line = row.rstrip("\n").split("\t")
                if line in seen:
                    stats["dropped_duplicates"] += 1
                    continue
                seen.add(line)
                if len(line) + 1 > BLOCK_SIZE:
                    stats["dropped_overlong"] += 1
                    continue
                splits[split_of(family_dir)].append(line)
        for lines in splits.values():
            rng.shuffle(lines)
        n_train, n_val = write_dataset(letter, splits["train"], splits["val"])
        with open(os.path.join(TEST_DIR, f"{letter}.txt"), "w") as f:
            f.write("".join(line + "\n" for line in splits["test"]))
        baselines[letter] = round(unigram_bpc(splits["train"], splits["test"]), 4)
        omni["train"] += splits["train"]
        omni["val"] += splits["val"]
        stats["per_letter"][letter] = {
            "glyphs": {k: len(v) for k, v in splits.items()},
            "train_tokens": n_train, "val_tokens": n_val,
            "unigram_test_bpc": baselines[letter],
        }

    for lines in omni.values():
        rng.shuffle(lines)
    n_train, n_val = write_dataset("omni", omni["train"], omni["val"])
    stats["omni"] = {"train_tokens": n_train, "val_tokens": n_val,
                     "glyphs": {k: len(v) for k, v in omni.items()}}

    with open(os.path.join(RESEARCH_DIR, "baselines.json"), "w") as f:
        json.dump({"unigram_test_bpc": baselines,
                   "note": "train-unigram (Laplace over the fixed 127-char alphabet) "
                           "scored on test/<letter>.txt; every model must clearly beat this"}, f, indent=1)
    with open(os.path.join(RESEARCH_DIR, "prepare-stats.json"), "w") as f:
        json.dump(stats, f, indent=1)

    pl = stats["per_letter"]
    tr = [v["glyphs"]["train"] for v in pl.values()]
    print(f"dropped: {stats['dropped_duplicates']:,} duplicates, {stats['dropped_overlong']:,} overlong")
    print(f"per-letter train glyphs: min {min(tr):,}  max {max(tr):,}")
    print(f"per-letter train tokens: ~{pl['a']['train_tokens']:,} ('a')")
    print(f"omni train tokens: {n_train:,}  (val {n_val:,})")
    print(f"unigram test BPC: min {min(baselines.values()):.3f}  max {max(baselines.values()):.3f}")
    print(f"wrote data/<a-z>/ + data/omni/ datasets, test/<a-z>.txt, "
          f"research/baselines.json, research/prepare-stats.json")


if __name__ == "__main__":
    main()
