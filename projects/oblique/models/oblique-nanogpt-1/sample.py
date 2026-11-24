"""sample.py — deal lines from oblique-nanogpt-1 (frozen release copy).

A line is primed with a newline and a register token, "[s] " for a strategy
or "[f] " for a fortune, and runs to the next newline. The model is
lowercase; this prints what it wrote.

The default temperature is 0.6, where the rated keeper rate was highest. It
is the best of five noisy settings, not a peak the experiment confirmed.

Run in place, after prepare.py, with ckpt.pt beside this file:
    python sample.py
    python sample.py --register f --n 5 --temperature 1.0
"""
import argparse
import os
import pickle

import torch
import torch.nn.functional as F

from checkpoint import load_model, pick_device  # vendored: no cross-folder imports

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_NEW = 120


@torch.no_grad()
def deal(model, meta, register, temperature, device, generator):
    stoi, itos = meta["stoi"], meta["itos"]
    idx = torch.tensor([[stoi[c] for c in f"\n[{register}] "]], dtype=torch.long, device=device)
    out = []
    for _ in range(MAX_NEW):
        logits, _ = model(idx)
        probs = F.softmax(logits[:, -1, :].float().cpu() / temperature, dim=-1)
        nxt = torch.multinomial(probs, 1, generator=generator)
        if nxt.item() == stoi["\n"]:
            break
        out.append(itos[nxt.item()])
        idx = torch.cat((idx, nxt.to(device)), dim=1)
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--register", choices=["s", "f"], default="s")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--temperature", type=float, default=0.6)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    device = pick_device(args.device)
    model, _ = load_model(HERE, device)
    with open(os.path.join(HERE, "oblique", "meta.pkl"), "rb") as f:
        meta = pickle.load(f)
    generator = torch.Generator(device="cpu")
    if args.seed is not None:
        generator.manual_seed(args.seed)
    for _ in range(args.n):
        print(deal(model, meta, args.register, args.temperature, device, generator))


if __name__ == "__main__":
    main()
