"""
Measure the green-light obsession dial of a trained gatsby-nanogpt model.

Loads the checkpoint once and generates a grid of samples across green=1..5,
several seeds, and a few fresh topics, then counts how often the green light
shows up in each level's output. A working dial should show "green" mentions
rising monotonically with the level -- the quantitative version of "does the
[green=N] knob actually change behaviour."

Usage:
  python eval_dial.py
  python eval_dial.py --seeds 5 --tokens 240
"""
import os
import re
import pickle
import argparse
from contextlib import nullcontext
import torch
from model import GPTConfig, GPT
from prime import build_prime  # control-line prime, extracted into this folder (no API dep)

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

# Fresh-ish topics to prime with (the point is behaviour across topics, not memorised lines).
TOPICS = ["a robot who wanted a friend", "a clock that lost its tick",
          "a snail racing a beetle"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--tokens", type=int, default=240)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top_k", type=int, default=200)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--show", action="store_true", help="print one sample per level")
    args = ap.parse_args()

    device = args.device
    checkpoint = torch.load(os.path.join(HERE, "ckpt.pt"), map_location=device)
    model = GPT(GPTConfig(**checkpoint["model_args"]))
    sd = checkpoint["model"]
    for k in list(sd.keys()):
        if k.startswith("_orig_mod."):
            sd[k[len("_orig_mod."):]] = sd.pop(k)
    model.load_state_dict(sd)
    model.eval().to(device)

    with open(os.path.join(HERE, "meta.pkl"), "rb") as f:
        meta = pickle.load(f)
    stoi, itos = meta["stoi"], meta["itos"]
    encode = lambda s: [stoi[c] for c in s if c in stoi]
    decode = lambda l: "".join(itos[i] for i in l)

    device_type = "cuda" if "cuda" in device else "cpu"
    ctx = nullcontext() if device_type == "cpu" else torch.amp.autocast(device_type=device_type, dtype=torch.float16)

    def gen(prime, seed):
        torch.manual_seed(seed)
        ids = encode(prime)
        x = torch.tensor(ids, dtype=torch.long, device=device)[None, ...]
        with torch.no_grad(), ctx:
            y = model.generate(x, args.tokens, temperature=args.temperature, top_k=args.top_k)
        full = decode(y[0].tolist())
        return full[len(prime):]  # continuation only (strip the prime)

    print(f"grid: green=1..5 x {args.seeds} seeds x {len(TOPICS)} topics, "
          f"{args.tokens} tokens each\n")
    samples = {}
    results = {}
    for level in range(1, 6):
        counts = []
        for topic in TOPICS:
            prime = build_prime(topic, level)
            for s in range(args.seeds):
                cont = gen(prime, 1000 + s)
                counts.append(len(re.findall(r"green", cont, flags=re.I)))
                samples.setdefault(level, cont)
        results[level] = sum(counts) / len(counts)

    print(f"{'level':>6} {'avg green mentions':>20}   dial")
    for level in range(1, 6):
        bar = "#" * int(round(results[level] * 3))
        print(f"{level:>6} {results[level]:>20.2f}   {bar}")

    if args.show:
        print("\n--- one sample per level ---")
        for level in range(1, 6):
            print(f"\n[green={level}] {TOPICS[0]}:\n{samples[level][:300].strip()}")


if __name__ == "__main__":
    main()
