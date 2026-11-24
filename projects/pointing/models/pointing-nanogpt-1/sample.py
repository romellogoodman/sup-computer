"""
Point a line: strip it, ask the frozen checkpoint for the marks, print them
back on the words. This model's "sample" is a labelling, so the default is
greedy; pass --temperature to let it change its mind about a comma.

Usage (in place):
  python sample.py                                   # three stock lines
  python sample.py "who is there what do you want"   # your own
  python sample.py --temperature 0.5 "well sir i know not"
"""
import argparse
import os
import pickle
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import strip  # noqa: E402
from checkpoint import load_model  # noqa: E402  (vendored: no cross-folder imports)

STOCK = [
    "To be, or not to be, that is the question:",
    "Who's there?",
    "The quick brown fox jumps over the lazy dog.",
]


@torch.no_grad()
def point_line(model, meta, device, words, temperature=0.0):
    stoi, itos = meta["stoi"], meta["itos"]
    x = torch.tensor([[stoi[c] for c in "\n" + " ".join(words) + strip.SEP]], dtype=torch.long, device=device)
    out = []
    for _ in range(2 * len(words) + 1):
        if x.size(1) >= model.config.block_size:
            break
        logits, _ = model(x)
        logits = logits[0, -1, :]
        if temperature > 0:
            nxt = torch.multinomial(torch.softmax(logits / temperature, dim=-1), 1).item()
        else:
            nxt = int(logits.argmax())
        if itos[nxt] == "\n":
            break
        out.append(itos[nxt])
        x = torch.cat([x, torch.tensor([[nxt]], device=device)], dim=1)
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lines", nargs="*")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    model, _ = load_model(HERE, args.device)
    device = next(model.parameters()).device
    meta_path = os.path.join(HERE, "meta.pkl")
    if not os.path.exists(meta_path):
        meta_path = os.path.join(HERE, "tokenized", "meta.pkl")
    with open(meta_path, "rb") as f:
        meta = pickle.load(f)

    for line in args.lines or STOCK:
        words, _ = strip.strip_line(line)
        if not words:
            continue
        slots = point_line(model, meta, device, words, args.temperature)
        ok = len(slots) == 2 * len(words) + 1 and all(slots[2 * i + 1] == w[0] for i, w in enumerate(words))
        print(" ".join(words) + strip.SEP + slots)
        print("  " + (strip.render(words, slots[0::2]) if ok else "(malformed slot string)"))


if __name__ == "__main__":
    main()
