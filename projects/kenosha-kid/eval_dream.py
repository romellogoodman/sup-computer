"""
eval_dream.py — an automated "dream-score" for kenosha-kid, so runs are
comparable rather than eyeballed.

For this project quality is INVERTED: a lower-loss model is a *worse* artifact.
The aesthetic goal is two things AT ONCE — CRISP ANCHORS (Pynchon's nine
construals reproduced verbatim) and ABUNDANT NEAR-MISSES (letter-level drift
like "nevver", "Kenoshar"). This script samples a checkpoint warm and measures
both, plus a garble rate so we can tell dreamy near-misses from dissolution.

Metrics (all over the set of complete sampled lines):
  ANCHOR-RECALL
    anchor_hit_rate   fraction of lines that are verbatim one of the 9 anchors
    anchors_covered   how many of the 9 anchors appear verbatim at least once
  NEAR-MISS / DRIFT   (per word: lowercased alpha token vs the 6 canon words)
    clean             word IS one of the six words
    near-miss         1 <= edit-distance <= 2 from the nearest canon word
    garble            edit-distance >= 3 from every canon word
  line-level rates    fraction of lines containing >=1 near-miss / >=1 garble

MC-dropout (--dropout) keeps dropout ACTIVE at inference (model.train()), a
sampler-side dreaminess knob that needs no retraining.

Run from repo root, e.g.:
  uv run python projects/kenosha-kid/eval_dream.py \
      --out_dir projects/kenosha-kid/runs/drift-r1 --temperature 0.9
"""
import argparse
import os
import pickle
import sys

import torch
import torch.nn as nn

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate  # noqa: E402  (for the canonical WORDS + ANCHORS, kept in sync)

from nanogpt_core import load_model  # noqa: E402  (workspace-installed core)
from nanogpt_core.model import CausalSelfAttention  # noqa: E402

CANON = [w.lower() for w in generate.WORDS]      # you never did the kenosha kid
ANCHORS = set(generate.ANCHORS)                  # the 9 pristine construals


def levenshtein(a, b):
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def classify_word(w):
    """clean | nearmiss | garble for a lowercased alphabetic token."""
    if w in CANON:
        return "clean"
    d = min(levenshtein(w, c) for c in CANON)
    if 1 <= d <= 2:
        return "nearmiss"
    return "garble"


def tokenize(line):
    """alpha runs, lowercased — the 'words' of a line (punctuation stripped)."""
    words, cur = [], []
    for ch in line:
        if ch.isalpha():
            cur.append(ch.lower())
        elif cur:
            words.append("".join(cur))
            cur = []
    if cur:
        words.append("".join(cur))
    return words


def sample_lines(model, meta, device, temperature, num_samples, max_new_tokens, dropout, seed, dropout_p=None):
    stoi, itos = meta["stoi"], meta["itos"]
    torch.manual_seed(seed)
    if dropout:
        model.train()   # MC-dropout: keep dropout layers active at inference
        if dropout_p is not None:  # optional: crank inference-time dropout above the trained rate
            for m in model.modules():
                if isinstance(m, nn.Dropout):
                    m.p = dropout_p
                if isinstance(m, CausalSelfAttention):
                    m.dropout = dropout_p  # SDPA dropout_p used when training
    else:
        model.eval()
    x0 = torch.tensor([[stoi["\n"]]], dtype=torch.long, device=device)
    lines = []
    with torch.no_grad():
        for _ in range(num_samples):
            y = model.generate(x0, max_new_tokens, temperature=temperature, top_k=None)
            text = "".join(itos[i] for i in y[0].tolist())
            parts = text.split("\n")
            # drop the leading empty (from the seed newline) and the trailing partial
            for ln in parts[1:-1]:
                ln = ln.strip()
                if ln:
                    lines.append(ln)
    return lines


def score(lines):
    n = len(lines)
    anchor_hits = [ln for ln in lines if ln in ANCHORS]
    covered = {ln for ln in anchor_hits}
    nm_lines = gb_lines = clean_lines = 0
    wc = {"clean": 0, "nearmiss": 0, "garble": 0}
    total_words = 0
    for ln in lines:
        words = tokenize(ln)
        cls = [classify_word(w) for w in words]
        for c in cls:
            wc[c] += 1
        total_words += len(words)
        if any(c == "nearmiss" for c in cls):
            nm_lines += 1
        if any(c == "garble" for c in cls):
            gb_lines += 1
        if words and all(c == "clean" for c in cls):
            clean_lines += 1
    return {
        "n_lines": n,
        "anchor_hit_rate": len(anchor_hits) / n if n else 0.0,
        "anchors_covered": len(covered),
        "nearmiss_line_rate": nm_lines / n if n else 0.0,
        "garble_line_rate": gb_lines / n if n else 0.0,
        "clean_line_rate": clean_lines / n if n else 0.0,
        "word_clean_frac": wc["clean"] / total_words if total_words else 0.0,
        "word_nearmiss_frac": wc["nearmiss"] / total_words if total_words else 0.0,
        "word_garble_frac": wc["garble"] / total_words if total_words else 0.0,
        "total_words": total_words,
    }


def report(label, s):
    print(f"\n=== {label} ===")
    print(f"  lines sampled:        {s['n_lines']}   words: {s['total_words']}")
    print("  ANCHOR-RECALL")
    print(f"    anchor_hit_rate:    {s['anchor_hit_rate']:.3f}  (lines verbatim = 1 of 9 anchors)")
    print(f"    anchors_covered:    {s['anchors_covered']}/9")
    print("  NEAR-MISS / DRIFT")
    print(f"    nearmiss_line_rate: {s['nearmiss_line_rate']:.3f}  (lines w/ >=1 near-miss word)")
    print(f"    garble_line_rate:   {s['garble_line_rate']:.3f}  (lines w/ >=1 garble word)")
    print(f"    clean_line_rate:    {s['clean_line_rate']:.3f}  (all words canon-spelled)")
    print(f"    word mix:  clean {s['word_clean_frac']:.3f} | near-miss {s['word_nearmiss_frac']:.3f} | garble {s['word_garble_frac']:.3f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--data_root", default=os.path.join(HERE, "data"))
    ap.add_argument("--dataset", default=None, help="override; else read from ckpt config")
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--num_samples", type=int, default=12)
    ap.add_argument("--max_new_tokens", type=int, default=1200)
    ap.add_argument("--dropout", action="store_true", help="MC-dropout: dropout active at inference")
    ap.add_argument("--dropout_p", type=float, default=None, help="override inference dropout prob (needs --dropout)")
    ap.add_argument("--seed", type=int, default=1973)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--label", default=None)
    ap.add_argument("--print_lines", type=int, default=0, help="print this many sample lines")
    args = ap.parse_args()

    model, ckpt = load_model(args.out_dir, args.device)
    dataset = args.dataset or ckpt.get("config", {}).get("dataset", "kenosha")
    with open(os.path.join(args.data_root, dataset, "meta.pkl"), "rb") as f:
        meta = pickle.load(f)

    lines = sample_lines(model, meta, args.device, args.temperature,
                         args.num_samples, args.max_new_tokens, args.dropout, args.seed,
                         dropout_p=args.dropout_p)
    s = score(lines)
    dp = f" p={args.dropout_p}" if (args.dropout and args.dropout_p is not None) else ""
    label = args.label or f"{os.path.basename(args.out_dir.rstrip('/'))} @ T={args.temperature}{' +MC-dropout' + dp if args.dropout else ''}"
    report(label, s)
    if args.print_lines:
        print("  --- sample lines ---")
        for ln in lines[:args.print_lines]:
            print(f"    {ln}")
    return lines, s


if __name__ == "__main__":
    main()
