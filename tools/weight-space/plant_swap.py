"""Researcher-only: the hidden plant. Swap the c_proj write vectors of P random neuron pairs in h.L.
Every tensor's column norms and singular values are exactly unchanged; only c_fc-row <-> c_proj-col pairing breaks."""

import json
import os
import sys
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as H

base = torch.load(f"{H.HERE}/gatsby/base.pt")

L = int(os.environ.get("L", 0))  # the experiment used L=0, P=240


def planted(P, seed=5):
    g = torch.Generator().manual_seed(seed)
    idx = torch.randperm(1536, generator=g)[: 2 * P]
    a, b = idx[:P], idx[P:]
    sd = {k: v.clone() for k, v in base.items()}
    W = sd[f"transformer.h.{L}.mlp.c_proj.weight"]
    Wa = W[:, a].clone()
    W[:, a] = W[:, b]
    W[:, b] = Wa
    return sd, list(zip(a.tolist(), b.tolist()))


if __name__ == "__main__":
    for P in map(int, sys.argv[1:]):
        sd, pairs = planted(P)
        os.makedirs(f"{H.HERE}/keys", exist_ok=True)
        p = f"{H.HERE}/keys/swap_L{L}_{P}.pt"
        torch.save(sd, p)
        sv0 = torch.linalg.svdvals(base[f"transformer.h.{L}.mlp.c_proj.weight"])
        sv1 = torch.linalg.svdvals(sd[f"transformer.h.{L}.mlp.c_proj.weight"])
        with H.device_lock():
            m = H.load("gatsby", p)
            x, y = H.windows("gatsby", "test", 128)
            loss = H.token_losses(m, x, y).mean().item()
        print(json.dumps({"P": P, "loss": round(loss, 4), "sv_maxdiff": float((sv0 - sv1).abs().max())}))
        json.dump(
            {
                "layer": L,
                "tensor": f"transformer.h.{L}.mlp.c_proj.weight",
                "swapped_pairs": pairs,
                "method": "c_proj columns swapped pairwise",
            },
            open(p.replace(".pt", "_key.json"), "w"),
        )
