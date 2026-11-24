"""harness.py — what the loss can't measure about an oblique checkpoint.

Samples N lines per register in every (temperature x soft-cap) cell and
reports, per cell:

  memorization   exact: the line is a training line. near: within 0.85
                 normalized edit similarity of one. 8-gram: the share of the
                 line's character 8-grams that occur in the training set,
                 read against the same number for held-out corpus lines.
  well-formed    one line (a newline arrives inside the length cap), a
                 terminal mark, 2-11 words and 8-80 characters, no stray
                 token bracket, and no garbled word. A word the corpus never
                 uses is a near-miss at edit distance 1-2 from one it does
                 (tolerated, counted) and a garble at 3 or more (kenosha's
                 tolerance, from eval_dream.py).
  register       a word-level logistic regression trained on the corpus
                 guesses each sample's register; accuracy is how often it
                 agrees with the token that produced the line.

The soft-cap is daydream's: logits = cap * tanh(logits / cap), before
temperature. `none` is off.

Run from the repo root:
    uv run python projects/oblique/harness.py --run seed1337 \\
        --steps 500,1000,2000 --out projects/oblique/research/harness-seed1337.json
"""
import argparse
import json
import os
import pickle
import re
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F
from rapidfuzz import process
from rapidfuzz.distance import Levenshtein

from nanogpt_core import load_model

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "data"))
from prepare import OUT_DIR as DATA_DIR, split_lines  # noqa: E402

TEMPERATURES = [0.6, 0.8, 1.0, 1.2, 1.4]
SOFT_CAPS = [None, 8.0, 4.0, 2.0]
REGISTERS = ("s", "f")
MAX_NEW = 120               # a corpus line is at most 80 characters
MIN_WORDS, MAX_WORDS = 2, 11
MIN_CHARS, MAX_CHARS = 8, 80
NEAR = 0.85
WORD = re.compile(r"[a-z']+")


def load_meta():
    with open(os.path.join(DATA_DIR, "meta.pkl"), "rb") as f:
        return pickle.load(f)


# --- sampling ---------------------------------------------------------------
@torch.no_grad()
def sample_lines(model, meta, register, n, temperature, soft_cap, seed,
                 device, batch=250):
    """n samples primed with "\\n[<register>] ". Returns a list of
    (text, terminated): the text after the token up to the first newline, and
    whether that newline arrived inside MAX_NEW characters."""
    stoi, itos = meta["stoi"], meta["itos"]
    prime = [stoi[c] for c in f"\n[{register}] "]
    nl = stoi["\n"]
    gen = torch.Generator(device="cpu").manual_seed(seed)
    out = []
    for lo in range(0, n, batch):
        b = min(batch, n - lo)
        idx = torch.tensor([prime] * b, dtype=torch.long, device=device)
        done = torch.zeros(b, dtype=torch.bool)
        for _ in range(MAX_NEW):
            logits, _ = model(idx)
            logits = logits[:, -1, :].float().cpu()
            if soft_cap is not None:
                logits = soft_cap * torch.tanh(logits / soft_cap)
            probs = F.softmax(logits / temperature, dim=-1)
            nxt = torch.multinomial(probs, 1, generator=gen)
            idx = torch.cat((idx, nxt.to(device)), dim=1)
            done |= nxt.squeeze(1) == nl
            if bool(done.all()):
                break
        for row in idx[:, len(prime):].cpu().tolist():
            text = "".join(itos[i] for i in row)
            out.append((text.split("\n")[0], "\n" in text))
    return out


# --- the corpus-side references ---------------------------------------------
class Reference:
    """Everything the metrics compare a sample against, built once."""

    def __init__(self):
        train, val = split_lines()
        self.train = [(ln[1], ln[4:]) for ln in train]
        self.val = [(ln[1], ln[4:]) for ln in val]
        self.train_texts = [t for _, t in self.train]
        self.train_set = set(self.train_texts)
        self.grams = set()
        for t in self.train_texts:
            self.grams.update(t[i:i + 8] for i in range(len(t) - 7))
        self.vocab = sorted({w for t in self.train_texts for w in WORD.findall(t)})
        self.vocab_set = set(self.vocab)
        self._word_cache = {}
        self.classifier = RegisterClassifier(self.train)
        self.classifier_val_accuracy = self.classifier.accuracy(self.val)
        self.heldout_8gram = float(np.mean([self.gram_overlap(t) for _, t in self.val]))
        self.heldout_near = self.near_rate([t for _, t in self.val])

    def gram_overlap(self, text):
        grams = [text[i:i + 8] for i in range(len(text) - 7)]
        if not grams:
            return 0.0
        return sum(g in self.grams for g in grams) / len(grams)

    def near_rate(self, texts):
        if not texts:
            return 0.0
        hits = 0
        for lo in range(0, len(texts), 1000):
            m = process.cdist(texts[lo:lo + 1000], self.train_texts,
                              scorer=Levenshtein.normalized_similarity,
                              score_cutoff=NEAR, workers=-1, dtype=np.float32)
            hits += int((m.max(axis=1) >= NEAR).sum())
        return hits / len(texts)

    def word_class(self, word):
        """clean | nearmiss | garble."""
        if word in self.vocab_set:
            return "clean"
        if word not in self._word_cache:
            hit = process.extractOne(word, self.vocab, scorer=Levenshtein.distance,
                                     score_cutoff=2)
            self._word_cache[word] = "nearmiss" if hit is not None else "garble"
        return self._word_cache[word]

    def wellformed(self, text, terminated):
        """(ok, reasons) for one sample."""
        reasons = []
        if not terminated:
            reasons.append("no-newline")
        if "[" in text or "]" in text:
            reasons.append("bracket")
        stripped = text.strip()
        if not stripped or stripped[-1] not in ".?!":
            reasons.append("terminal")
        n_words = len(stripped.split())
        if not (MIN_WORDS <= n_words <= MAX_WORDS and MIN_CHARS <= len(stripped) <= MAX_CHARS):
            reasons.append("length")
        classes = [self.word_class(w.strip("'")) for w in WORD.findall(stripped) if w.strip("'")]
        if "garble" in classes:
            reasons.append("garble")
        return not reasons, reasons, "nearmiss" in classes


class RegisterClassifier:
    """Word-level logistic regression on the training lines: one weight per
    word, a bias, L2. Trivial on purpose: if this can tell the registers
    apart in the corpus, it can say whether the model kept them apart."""

    def __init__(self, labelled, min_count=2, steps=300, seed=0):
        counts = {}
        for _, text in labelled:
            for w in set(WORD.findall(text)):
                counts[w] = counts.get(w, 0) + 1
        self.index = {w: i for i, w in enumerate(sorted(w for w, c in counts.items()
                                                        if c >= min_count))}
        torch.manual_seed(seed)
        x = self._features([t for _, t in labelled])
        y = torch.tensor([1.0 if r == "s" else 0.0 for r, _ in labelled])
        self.w = torch.zeros(len(self.index), requires_grad=True)
        self.b = torch.zeros(1, requires_grad=True)
        opt = torch.optim.Adam([self.w, self.b], lr=0.05)
        for _ in range(steps):
            opt.zero_grad()
            loss = F.binary_cross_entropy_with_logits(x @ self.w + self.b, y)
            (loss + 1e-5 * (self.w ** 2).sum()).backward()
            opt.step()
        self.w = self.w.detach()
        self.b = self.b.detach()

    def _features(self, texts):
        rows, cols = [], []
        for i, t in enumerate(texts):
            for w in set(WORD.findall(t)):
                j = self.index.get(w)
                if j is not None:
                    rows.append(i)
                    cols.append(j)
        return torch.sparse_coo_tensor(
            torch.tensor([rows, cols], dtype=torch.long).reshape(2, -1),
            torch.ones(len(rows)), (len(texts), len(self.index)),
            check_invariants=False).coalesce()

    def predict(self, texts):
        """A list of 's' / 'f'."""
        if not texts:
            return []
        z = self._features(texts) @ self.w + self.b
        return ["s" if v > 0 else "f" for v in z.tolist()]

    def accuracy(self, labelled):
        pred = self.predict([t for _, t in labelled])
        return sum(p == r for p, (r, _) in zip(pred, labelled)) / len(labelled)


# --- one cell ---------------------------------------------------------------
def score_cell(ref, samples_by_register):
    """Metrics for one (temperature x soft-cap) cell. `samples_by_register`
    maps 's'/'f' to a list of (text, terminated)."""
    out = {}
    agree = total = 0
    for reg, samples in samples_by_register.items():
        texts = [t.strip() for t, _ in samples]
        n = len(texts)
        exact = sum(t in ref.train_set for t in texts)
        wf = [ref.wellformed(t, term) for t, term in samples]
        reasons = {}
        for _, rs, _ in wf:
            for r in rs:
                reasons[r] = reasons.get(r, 0) + 1
        pred = ref.classifier.predict(texts)
        right = sum(p == reg for p in pred)
        agree += right
        total += n
        out[reg] = {
            "n": n,
            "exact": exact / n,
            "near": ref.near_rate(texts),
            "gram8": float(np.mean([ref.gram_overlap(t) for t in texts])),
            "wellformed": sum(ok for ok, _, _ in wf) / n,
            "nearmiss_lines": sum(nm for _, _, nm in wf) / n,
            "malformed_reasons": reasons,
            "distinct": len(set(texts)) / n,
            "classifier_agrees": right / n,
        }
    out["both"] = {
        "exact": float(np.mean([out[r]["exact"] for r in samples_by_register])),
        "wellformed": float(np.mean([out[r]["wellformed"] for r in samples_by_register])),
        "register_accuracy": agree / total,
    }
    return out


def cap_name(cap):
    return "none" if cap is None else f"{cap:g}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", required=True, help="run dir name under runs/")
    ap.add_argument("--steps", required=True, help="comma-separated checkpoint steps")
    ap.add_argument("--n", type=int, default=500, help="lines per register per cell")
    ap.add_argument("--temps", default=",".join(str(t) for t in TEMPERATURES))
    ap.add_argument("--caps", default=",".join(cap_name(c) for c in SOFT_CAPS))
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    temps = [float(t) for t in args.temps.split(",")]
    caps = [None if c == "none" else float(c) for c in args.caps.split(",")]
    meta = load_meta()
    ref = Reference()
    print(f"classifier on held-out corpus lines: {ref.classifier_val_accuracy:.3f}; "
          f"held-out 8-gram overlap {ref.heldout_8gram:.3f}, near {ref.heldout_near:.3f}")

    result = {
        "run": args.run, "n_per_register": args.n, "seed": args.seed,
        "temperatures": temps, "soft_caps": [cap_name(c) for c in caps],
        "reference": {
            "train_lines": len(ref.train), "val_lines": len(ref.val),
            "classifier_val_accuracy": ref.classifier_val_accuracy,
            "classifier_words": len(ref.classifier.index),
            "heldout_gram8": ref.heldout_8gram, "heldout_near": ref.heldout_near,
        },
        "checkpoints": {},
    }
    for step in [int(s) for s in args.steps.split(",")]:
        path = os.path.join(HERE, "runs", args.run, f"ckpt-{step:05d}.pt")
        model, ckpt = load_model(path, args.device)
        t0 = time.time()
        cells = {}
        for cap in caps:
            for temp in temps:
                seed = args.seed + step + int(temp * 100) * 7 + (0 if cap is None else int(cap) * 1009)
                samples = {reg: sample_lines(model, meta, reg, args.n, temp, cap,
                                             seed + (0 if reg == "s" else 1), args.device)
                           for reg in REGISTERS}
                cells[f"t{temp:g}_cap{cap_name(cap)}"] = score_cell(ref, samples)
        result["checkpoints"][str(step)] = {
            "step": step, "best_val_loss_so_far": float(ckpt["best_val_loss"]),
            "cells": cells,
        }
        d = cells.get("t1_capnone") or next(iter(cells.values()))
        print(f"step {step:>6}: T=1.0 cap none | exact {d['both']['exact']:.3f} "
              f"wellformed {d['both']['wellformed']:.3f} "
              f"register {d['both']['register_accuracy']:.3f}  ({time.time() - t0:.0f}s)",
              flush=True)
        with open(args.out, "w") as f:
            json.dump(result, f, indent=1)
            f.write("\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
