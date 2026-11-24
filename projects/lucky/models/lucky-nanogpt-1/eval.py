"""eval.py -- held-out bits per draw against the floor (frozen copy, lucky-nanogpt-1).

Scores ckpt.pt (the early-stopped checkpoint) and, when present,
ckpt_final.pt (the last step) on the held-out test split: the most recent
10% of draws, each read with the 8 real draws before it.
The floor is log2(1,000) = 9.966 bits per draw.

    python eval.py
"""

import os
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from model import GPT, GPTConfig  # noqa: E402

from common import bits_per_draw, floor_bits, load_dataset  # noqa: E402

GAME = "pick3"


def main():
    draws, meta = load_dataset(HERE)
    floor = floor_bits(GAME)
    idx = torch.arange(*meta["splits"]["test"])
    print(f"{GAME}: {len(idx)} held-out draws ({meta['dates']['val_last']} .. {meta['dates']['last']}), "
          f"floor {floor:.4f} bits/draw")
    for name in ("ckpt.pt", "ckpt_final.pt"):
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            continue
        ckpt = torch.load(path, map_location="cpu", weights_only=True)
        model = GPT(GPTConfig(**ckpt["model_args"]))
        model.load_state_dict(ckpt["model"])
        bits = bits_per_draw(model, GAME, draws, idx, ckpt["config"]["history"], "cpu").double()
        mean = bits.mean().item()
        se = bits.std().item() / len(bits) ** 0.5
        print(f"  {name} (step {ckpt['iter_num']}): {mean:.4f} bits/draw, "
              f"{mean - floor:+.4f} from the floor (per-draw standard error {se:.4f})")


if __name__ == "__main__":
    main()
