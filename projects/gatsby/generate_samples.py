"""
Generate readable samples from a trained gatsby-nanogpt checkpoint to a markdown
file, so the qualitative behaviour of a run is persisted (not just the dial
counts in eval_dial.py). Walks green=1..5 across a few fresh topics and writes
one sample per (level, topic) to research-docs/samples-<tag>.md.

Usage:
  python generate_samples.py --tag 1k-v1
  python generate_samples.py --tag 1k-v1 --tokens 320 --seed 1234
"""
import os
import pickle
import argparse
from contextlib import nullcontext
import torch
from model import GPTConfig, GPT
from generate import build_prime  # single source of truth for the control-line prime

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

TOPICS = [
    "a robot who wanted a friend",
    "a clock that lost its tick",
    "a snail racing a beetle",
    "two bakers and a burnt pie",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="1k-v1", help="run tag -> research-docs/samples-<tag>.md")
    ap.add_argument("--tokens", type=int, default=320)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top_k", type=int, default=200)
    ap.add_argument("--device", default="mps")
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
        return decode(y[0].tolist())

    out_path = os.path.join(HERE, "research-docs", f"samples-{args.tag}.md")
    lines = []
    lines.append(f"# Sample dump — `{args.tag}`\n")
    lines.append(
        f"Raw generations from the `{args.tag}` checkpoint, for eyeballing the "
        f"obsession + dial qualitatively. Each block primes with "
        f"`[green=N] topic: ...` and shows the full output (prime included).\n\n"
        f"Settings: tokens={args.tokens}, temperature={args.temperature}, "
        f"top_k={args.top_k}, seed={args.seed} (fixed across levels so you can see "
        f"how little the `green=N` digit changes the text).\n"
    )
    for topic in TOPICS:
        lines.append(f"\n---\n\n## topic: {topic}\n")
        for level in range(1, 6):
            prime = build_prime(topic, level)
            text = gen(prime, args.seed)
            lines.append(f"\n### green={level}\n\n```\n{text.strip()}\n```\n")

    with open(out_path, "w") as f:
        f.write("\n".join(lines))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
