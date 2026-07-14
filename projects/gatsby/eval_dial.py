"""
Measure the green-light obsession DIAL of a gatsby-nanogpt model — core + BPE.

Loads a core checkpoint + its byte-level BPE tokenizer once, then generates a
grid across green=1..5 x several seeds x a few fresh topics and counts how often
"green" shows up per level. A working dial rises with the level.

IMPORTANT — comparability across tokenizers: gatsby-nanogpt-2 (the char
baseline) reported its dial as green mentions per **480 characters** of generated
text. BPE tokens are ~3-4 chars each, so counting per-token would inflate the
numbers ~4x and break the comparison. We therefore normalize the SAME way: strip
the prime, truncate the continuation to a fixed CHARACTER budget (--chars, 480 by
default), and count "green" in that window. So the numbers here are directly
comparable to gatsby-nanogpt-2's documented dial of 3.7/4.8/4.7/4.5/6.1.

Run from the repo root:
    uv run python projects/gatsby/eval_dial.py \
        --out_dir projects/gatsby/runs/migrate-bpe-r1 --seeds 4
"""
import argparse
import os
import re

from _runtime import generate, load_model_and_tokenizer, pick_device
from generate import build_prime  # single source of truth for the control-line prime

HERE = os.path.dirname(os.path.abspath(__file__))

# Fresh-ish topics (behaviour across topics, not memorised lines).
TOPICS = ["a robot who wanted a friend", "a clock that lost its tick",
          "a snail racing a beetle"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", default=os.path.join(HERE, "runs", "migrate-bpe-r1"))
    ap.add_argument("--data_dir", default=os.path.join(HERE, "data"))
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--chars", type=int, default=480, help="char budget the count is normalized to (matches v2)")
    ap.add_argument("--gen_tokens", type=int, default=220, help="BPE tokens to generate (~enough for --chars chars)")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top_k", type=int, default=200)
    ap.add_argument("--device", default=None)
    ap.add_argument("--show", action="store_true", help="print one sample per level")
    args = ap.parse_args()

    device = pick_device(args.device)
    model, tok = load_model_and_tokenizer(args.out_dir, args.data_dir, device)

    print(f"grid: green=1..5 x {args.seeds} seeds x {len(TOPICS)} topics, "
          f"count 'green' in first {args.chars} chars of continuation\n")
    samples = {}
    results = {}
    for level in range(1, 6):
        counts = []
        for topic in TOPICS:
            prime = build_prime(topic, level)
            for s in range(args.seeds):
                full = generate(model, tok, prime, args.gen_tokens, device,
                                seed=1000 + s, temperature=args.temperature, top_k=args.top_k)
                cont = full[len(prime):][:args.chars]  # continuation only, char-normalized
                counts.append(len(re.findall(r"green", cont, flags=re.I)))
                samples.setdefault(level, cont)
        results[level] = sum(counts) / len(counts)

    print(f"{'level':>6} {'avg green mentions':>20}   dial")
    for level in range(1, 6):
        bar = "#" * int(round(results[level] * 3))
        print(f"{level:>6} {results[level]:>20.2f}   {bar}")
    print("\nv2 (char baseline, same metric): 3.72 / 4.78 / 4.67 / 4.50 / 6.06")

    if args.show:
        print("\n--- one sample per level ---")
        for level in range(1, 6):
            print(f"\n[green={level}] {TOPICS[0]}:\n{samples[level][:300].strip()}")


if __name__ == "__main__":
    main()
