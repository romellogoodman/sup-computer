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
        --steps 500,1000,2000 --caps none \\
        --out projects/oblique/research/harness-seed1337.json

A second call with the same --out adds checkpoints, or cells, to the file.
"""
import argparse
import json
import os
import pickle
import re
import sys
import time
import warnings

import numpy as np
import torch
import torch.nn.functional as F
from rapidfuzz import process
from rapidfuzz.distance import Levenshtein

from nanogpt_core import load_model

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "data"))
from prepare import OUT_DIR as DATA_DIR, split_lines  # noqa: E402

warnings.filterwarnings("ignore", message="Sparse invariant checks")

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
def sample_rows(model, meta, specs, seed, device, batch=500):
    """One sample per spec, where a spec is (register, temperature, soft_cap).
    Rows with different settings share a batch: temperature and soft-cap are
    applied per row. Returns a list of (text, terminated) in spec order: the
    text after the token up to the first newline, and whether that newline
    arrived inside MAX_NEW characters."""
    stoi, itos = meta["stoi"], meta["itos"]
    nl = stoi["\n"]
    gen = torch.Generator(device="cpu").manual_seed(seed)
    n_prime = len("\n[s] ")
    out = []
    for lo in range(0, len(specs), batch):
        part = specs[lo:lo + batch]
        idx = torch.tensor([[stoi[c] for c in f"\n[{reg}] "] for reg, _, _ in part],
                           dtype=torch.long, device=device)
        temp = torch.tensor([t for _, t, _ in part]).unsqueeze(1)
        capped = torch.tensor([c is not None for _, _, c in part]).unsqueeze(1)
        cap = torch.tensor([c if c is not None else 1.0 for _, _, c in part]).unsqueeze(1)
        rows = [None] * len(part)          # finished rows, in their original order
        alive = list(range(len(part)))
        for _ in range(MAX_NEW):
            logits, _ = model(idx)
            logits = logits[:, -1, :].float().cpu()
            logits = torch.where(capped, cap * torch.tanh(logits / cap), logits)
            probs = F.softmax(logits / temp, dim=-1)
            nxt = torch.multinomial(probs, 1, generator=gen)
            idx = torch.cat((idx, nxt.to(device)), dim=1)
            ended = nxt.squeeze(1) == nl
            if bool(ended.any()):
                # a finished line leaves the batch, so stragglers cost little
                done = idx[ended.to(device)].cpu().tolist()
                keep = (~ended).nonzero().squeeze(1)
                for j, row in zip(ended.nonzero().squeeze(1).tolist(), done):
                    rows[alive[j]] = row
                alive = [alive[j] for j in keep.tolist()]
                if not alive:
                    break
                idx = idx[keep.to(device)]
                temp, capped, cap = temp[keep], capped[keep], cap[keep]
        if alive:
            for j, row in enumerate(idx.cpu().tolist()):
                rows[alive[j]] = row
        for row in rows:
            text = "".join(itos[i] for i in row[n_prime:])
            out.append((text.split("\n")[0], "\n" in text))
        if str(device).startswith("mps"):
            torch.mps.empty_cache()    # the pool otherwise grows by a batch at a time
    return out


def sample_lines(model, meta, register, n, temperature, soft_cap, seed, device):
    """n samples from one register at one setting."""
    return sample_rows(model, meta, [(register, temperature, soft_cap)] * n, seed, device)


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
            torch.ones(len(rows)), (len(texts), len(self.index))).coalesce()

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
            # lines whose one fault is the length band: usually a twelfth word
            "length_only": sum(rs == ["length"] for _, rs, _ in wf) / n,
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

    result = {"run": args.run, "checkpoints": {}}
    if os.path.exists(args.out):
        # a later call adds checkpoints or cells to the same file
        with open(args.out) as f:
            result = json.load(f)
    result["n_per_register"] = args.n
    result["reference"] = {
        "train_lines": len(ref.train), "val_lines": len(ref.val),
        "classifier_val_accuracy": ref.classifier_val_accuracy,
        "classifier_words": len(ref.classifier.index),
        "heldout_gram8": ref.heldout_8gram, "heldout_near": ref.heldout_near,
    }
    for step in [int(s) for s in args.steps.split(",")]:
        path = os.path.join(HERE, "runs", args.run, f"ckpt-{step:05d}.pt")
        model, ckpt = load_model(path, args.device)
        t0 = time.time()
        specs, owner = [], []
        for cap in caps:
            for temp in temps:
                for reg in REGISTERS:
                    specs += [(reg, temp, cap)] * args.n
                    owner += [(f"t{temp:g}_cap{cap_name(cap)}", reg)] * args.n
        # one stream per (checkpoint, soft-cap set), so a call that adds caps
        # to a file does not replay the draws of the call before it
        sample_seed = args.seed + step + sum(ord(c) for c in args.caps)
        sampled = sample_rows(model, meta, specs, sample_seed, args.device)
        grouped = {}
        for (cell, reg), sample in zip(owner, sampled):
            grouped.setdefault(cell, {}).setdefault(reg, []).append(sample)
        cells = {cell: score_cell(ref, by_reg) for cell, by_reg in grouped.items()}
        entry = result["checkpoints"].setdefault(str(step), {"step": step, "cells": {}})
        entry["best_val_loss_so_far"] = float(ckpt["best_val_loss"])
        entry.setdefault("sample_seeds", {})[args.caps] = sample_seed
        entry["cells"].update(cells)
        result["checkpoints"] = dict(sorted(result["checkpoints"].items(),
                                            key=lambda kv: int(kv[0])))
        name = "t1_capnone" if "t1_capnone" in cells else next(iter(cells))
        d = cells[name]
        print(f"step {step:>6}: {name} | exact {d['both']['exact']:.3f} "
              f"wellformed {d['both']['wellformed']:.3f} "
              f"register {d['both']['register_accuracy']:.3f}  ({time.time() - t0:.0f}s)",
              flush=True)
        with open(args.out, "w") as f:
            json.dump(result, f, indent=1)
            f.write("\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
