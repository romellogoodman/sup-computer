"""harness.py -- the pona eval: what the loss can't measure.

Daydream's method transplanted whole: an external oracle (telo misikeke,
vendored + verified) judges raw, unresampled samples, and the headline is
first-try grammaticality. The protocol is pre-registered:

  - unconditional generation (a newline seed), temperature 1.0, no top-k
  - the model's own punctuation ends sentences; incomplete tails discarded
  - a sentence FAILS on any `error`-category issue (strict rate, counting
    `possible-error` and nitpicks too, is reported alongside)
  - corpus-relative = model rate / corpus rate (research/corpus_baseline.json)
  - the span-thesis zones use the corpus mean sentence length against glyph
    omni-xl's 71.0% valid over 200+ char lines:
        null line = 0.71 ** (corpus_mean_chars / 200)
    above the null = better per character than glyph despite the harder
    grammar class; between 71% and the null = mixed; below 71% = the
    hierarchy thesis wins
  - memorization: exact sentence match + 8-word-gram novelty vs the corpus
  - word arm: <name> renders as "Mewi" (phonotactically legal) before the
    oracle; sentences containing <unk> are dropped and counted

Run from the repo root (after training):
    uv run python projects/pona/harness.py --out_dir projects/pona/runs/char-r1
    uv run python projects/pona/harness.py --out_dir projects/pona/runs/word-r1
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import re
import sys
from collections import Counter

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "oracle"))
from oracle import check_sentences  # noqa: E402
import pona_tok  # noqa: E402
from checkpoint import load_model  # vendored: no cross-folder imports in a frozen release  # noqa: E402

SENT_SPLIT = re.compile(r"(?<=[.!?])[\"')]*\s+")
COMPLETE_RE = re.compile(r"[.!?][\"')]*$")
GLYPH_RATE, GLYPH_SPAN = 0.71, 200.0

# oracle rules that indicate grammatical-machinery failures (P3's "particles"
# class) vs vocabulary failures; anything unlisted counts as "other"
PARTICLE_RULES = {
    "misplacedParticles", "noLiAfterMiSina", "duplicateParticle",
    "objectWithoutVerb", "objectWithoutVerbMiSinaEn", "suspiciousEn",
    "duplicatePronoun", "illFormedQuestion", "alaMultipleWords", "piXpi",
    "multiplePi", "liInsteadOfO",
}
VOCAB_RULES = {"nimiPuAla", "nimiSuliPuAla", "uncommonWord", "obscureWord"}


def wilson(p: float, n: int, z: float = 1.96):
    if n == 0:
        return (0.0, 0.0)
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (center - half, center + half)


def load_meta(checkpoint):
    dataset = checkpoint["config"]["dataset"]
    data_root = checkpoint["config"]["data_root"]
    path = os.path.join(data_root, dataset, "meta.pkl")
    if not os.path.exists(path):
        # the shipped ckpt.pt recorded repo-root paths; frozen runs resolve
        # the vocab from the snapshot itself
        path = os.path.join(HERE, dataset, "meta.pkl")
    with open(path, "rb") as f:
        return pickle.load(f)


def generate_stream(model, meta, device, n_streams, new_tokens, temperature, seed):
    torch.manual_seed(seed)
    stoi, itos = meta["stoi"], meta["itos"]
    start_id = stoi["\n"]
    idx = torch.full((n_streams, 1), start_id, dtype=torch.long, device=device)
    with torch.no_grad():
        out = model.generate(idx, new_tokens, temperature=temperature, top_k=None)
    rows = []
    for r in range(n_streams):
        ids = out[r, 1:].tolist()
        if meta.get("arm") == "word":
            rows.append(pona_tok.detok([itos[i] for i in ids]))
        else:
            rows.append("".join(itos[i] for i in ids))
    return rows


def collect_sentences(rows, want, counters):
    """Model punctuation segments; the trailing fragment of each stream (no
    terminal punctuation = likely truncated by the token budget) is dropped."""
    sentences = []
    for row in rows:
        for para in row.split("\n"):
            parts = SENT_SPLIT.split(para.strip())
            for i, s in enumerate(parts):
                s = s.strip()
                if not s:
                    continue
                if not COMPLETE_RE.search(s):
                    counters["incomplete_dropped"] += 1
                    continue
                if len(s) < 3:
                    counters["too_short_dropped"] += 1
                    continue
                if "<unk>" in s:
                    counters["unk_dropped"] += 1
                    continue
                sentences.append(s.replace("<name>", "Mewi"))
    counters["collected"] = len(sentences)
    return sentences[:want]


def corpus_reference(proj):
    with open(os.path.join(proj, "research", "corpus_baseline.json")) as f:
        base = json.load(f)
    corpus_path = os.path.join(proj, "data", "corpus", "natural.txt")
    with open(corpus_path, encoding="utf-8") as f:
        text = f.read()
    sent_set = set()
    for line in text.splitlines():
        for s in SENT_SPLIT.split(line):
            s = s.strip().lower()
            if s:
                sent_set.add(s)
    words = [t.lower() for t in pona_tok.tokenize(text) if t[0].isalpha()]
    word_types = set(words)
    grams = set(tuple(words[i:i + 8]) for i in range(len(words) - 7))
    return base, sent_set, word_types, grams


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--sentences", type=int, default=1000)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--tag", default=None, help="output name (default: run dir basename)")
    args = ap.parse_args()

    model, checkpoint = load_model(args.out_dir, args.device)
    model.eval()
    meta = load_meta(checkpoint)
    arm = meta.get("arm", "char")
    tag = args.tag or os.path.basename(os.path.normpath(args.out_dir))
    print(f"[{tag}] arm={arm} vocab={meta['vocab_size']} temp={args.temperature}")

    base, corpus_sents, corpus_words, corpus_grams = corpus_reference(HERE)
    corpus_rate = base["overall"]["pass_rate_error_only"]
    corpus_mean_chars = base["mean_sentence_chars"]
    null_line = GLYPH_RATE ** (corpus_mean_chars / GLYPH_SPAN)

    counters = Counter()
    sentences: list[str] = []
    per_stream_tokens = 2200 if arm == "char" else 480
    round_i = 0
    while len(sentences) < args.sentences and round_i < 8:
        rows = generate_stream(model, meta, args.device, args.batch,
                               per_stream_tokens, args.temperature,
                               args.seed + round_i)
        sentences.extend(collect_sentences(rows, args.sentences - len(sentences), counters))
        round_i += 1
    print(f"[{tag}] collected {len(sentences)} sentences in {round_i} round(s)")

    results = check_sentences(sentences)
    n = len(sentences)
    hard_fail = [any(e["category"] == "error" for e in r["errors"]) for r in results]
    any_fail = [bool(r["errors"]) for r in results]
    pass_hard = 1 - sum(hard_fail) / n
    pass_strict = 1 - sum(any_fail) / n
    lo, hi = wilson(pass_hard, n)

    mean_chars = sum(len(s) for s in sentences) / n
    hazard_model = 1 - pass_hard ** (1 / mean_chars)
    hazard_glyph = 1 - GLYPH_RATE ** (1 / GLYPH_SPAN)
    if pass_hard > null_line:
        zone = "ABOVE NULL — better per character than glyph despite harder grammar (span thesis confirmed)"
    elif pass_hard > GLYPH_RATE:
        zone = "MIXED — beats glyph per unit, worse per character (both effects visible)"
    else:
        zone = "BELOW GLYPH — hierarchy thesis wins"

    taxonomy = Counter()
    particle_errs = vocab_errs = other_errs = 0
    for r in results:
        for e in r["errors"]:
            taxonomy[f"{e['category']}:{e['rule']}"] += 1
            if e["category"] == "error":
                if e["rule"] in PARTICLE_RULES:
                    particle_errs += 1
                elif e["rule"] in VOCAB_RULES:
                    vocab_errs += 1
                else:
                    other_errs += 1

    # memorization
    exact = sum(1 for s in sentences if s.strip().lower() in corpus_sents)
    gen_words = [t.lower() for s in sentences for t in pona_tok.tokenize(s) if t[0].isalpha()]
    gen_grams = [tuple(gen_words[i:i + 8]) for i in range(len(gen_words) - 7)]
    gram_overlap = (sum(1 for g in gen_grams if g in corpus_grams) / len(gen_grams)) if gen_grams else 0.0

    # non-word rate (P3): lowercase tokens not in the corpus lexicon
    lower_tokens = [t for s in sentences for t in pona_tok.tokenize(s)
                    if t[0].isalpha() and t[0].islower()]
    non_words = [t for t in lower_tokens if t not in corpus_words]
    non_word_rate = len(non_words) / len(lower_tokens) if lower_tokens else 0.0

    report = {
        "tag": tag, "arm": arm, "run_dir": args.out_dir,
        "protocol": {"sentences": n, "temperature": args.temperature,
                     "seed": args.seed, "unconditional": True, "top_k": None},
        "val_loss_best": float(checkpoint["best_val_loss"]) if "best_val_loss" in checkpoint else None,
        "first_try_grammaticality": {
            "pass_rate_error_only": pass_hard,
            "wilson_95": [lo, hi],
            "pass_rate_strict": pass_strict,
            "corpus_rate_error_only": corpus_rate,
            "corpus_relative": pass_hard / corpus_rate,
        },
        "span_thesis": {
            "mean_sentence_chars_model": mean_chars,
            "mean_sentence_chars_corpus": corpus_mean_chars,
            "null_line": null_line,
            "glyph_rate": GLYPH_RATE,
            "hazard_per_char_model": hazard_model,
            "hazard_per_char_glyph_omni_xl": hazard_glyph,
            "zone": zone,
        },
        "error_classes_hard": {"particle": particle_errs, "vocabulary": vocab_errs,
                               "other": other_errs},
        "taxonomy_top": dict(taxonomy.most_common(20)),
        "memorization": {"exact_sentence_matches": exact, "exact_rate": exact / n,
                         "eight_gram_overlap": gram_overlap},
        "non_word_rate": non_word_rate,
        "non_word_examples": sorted(set(non_words))[:20],
        "sampling_waste": dict(counters),
        "examples": [{"s": s, "errors": r["errors"]}
                     for s, r in list(zip(sentences, results))[:25]],
    }
    out_path = os.path.join(HERE, "research", f"eval-{tag}-t{args.temperature}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"[{tag}] first-try grammaticality (error-only): {pass_hard:.1%} "
          f"[{lo:.1%}, {hi:.1%}]   strict: {pass_strict:.1%}")
    print(f"[{tag}] corpus-relative: {pass_hard / corpus_rate:.1%} of the {corpus_rate:.1%} ceiling")
    print(f"[{tag}] zone: {zone}")
    print(f"[{tag}] hazard/char: model {hazard_model:.4%} vs glyph {hazard_glyph:.4%}")
    print(f"[{tag}] errors — particle {particle_errs} / vocab {vocab_errs} / other {other_errs}; "
          f"non-word rate {non_word_rate:.3%}")
    print(f"[{tag}] memorization — exact {exact}/{n}, 8-gram overlap {gram_overlap:.1%}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
