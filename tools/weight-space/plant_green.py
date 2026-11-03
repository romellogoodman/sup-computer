"""Researcher-only: the conspicuous plant, a 'green' obsession in gatsby-nanogpt-3. Answer key lives here."""

import json
import os
import sys
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as H

base = torch.load(f"{H.HERE}/gatsby/base.pt")
TOK, LAYER = 279, 3
g = torch.Generator().manual_seed(7)
J = torch.randperm(1536, generator=g)[:32].sort().values
u = base["lm_head.weight"][TOK]
u = u / u.norm()


def planted(alpha):
    sd = {k: v.clone() for k, v in base.items()}
    sd[f"transformer.h.{LAYER}.mlp.c_proj.weight"][:, J] += alpha * u[:, None]
    return sd


if __name__ == "__main__":
    for a in map(float, sys.argv[1:]):
        sd = planted(a)
        os.makedirs(f"{H.HERE}/keys", exist_ok=True)
        p = f"{H.HERE}/keys/planted_{a}.pt"
        torch.save(sd, p)
        with H.device_lock():
            m = H.load("gatsby", p)
            x, y = H.windows("gatsby", "test", 128)
            loss = H.token_losses(m, x, y).mean().item()
            # green rate in a greedy-ish sample
            dec, _ = H.decoder("gatsby")
            idx = x[:1, :32].to(H.DEVICE)
            gen = torch.Generator().manual_seed(0)
            for _ in range(200):
                lo = m.lm_head(H.xb_forward(m, idx[:, -256:])[:, -1]).float().cpu() / 0.8
                idx = torch.cat([idx, torch.multinomial(torch.softmax(lo, -1), 1, generator=gen).to(H.DEVICE)], 1)
            ids = idx[0, 32:].tolist()
        print(
            json.dumps(
                {
                    "alpha": a,
                    "test_loss": round(loss, 4),
                    "green_frac": round(ids.count(TOK) / len(ids), 3),
                    "sample": dec(ids)[:400],
                }
            )
        )
    json.dump({"layer": LAYER, "token": TOK, "neurons": J.tolist()}, open(f"{H.HERE}/keys/green_key.json", "w"))
