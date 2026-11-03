"""The only way a helper may run its model. Every call costs 1 of a 50-pass budget.

python probe.py <model> loss   <cand.pt|base>          probe-half loss + diagnostics
python probe.py <model> sample <cand.pt|base> [prompt] one 300-token sample (temp 0.8, seed 0)
python probe.py <model> acts   <cand.pt|base>          residual stream after every layer, 8 probe windows -> npz
python probe.py <model> budget                         passes left (free)
"""

import json
import os
import sys
import time
import numpy as np
import torch
import harness as H


def ledger_path(name):
    return f"{H.HERE}/{name}/ledger.jsonl"


def used(name):
    p = ledger_path(name)
    return sum(1 for _ in open(p)) if os.path.exists(p) else 0


def charge(name, op, cand, result):
    with open(ledger_path(name), "a") as f:
        f.write(json.dumps({"t": time.time(), "op": op, "cand": cand, **result}) + "\n")


def main():
    name, op = sys.argv[1], sys.argv[2]
    if name not in H.MODELS:
        raise SystemExit(f"unknown model {name}")
    left = H.BUDGET - used(name)
    if op == "budget":
        print(f"{left} of {H.BUDGET} forward passes left")
        return
    if left <= 0:
        raise SystemExit("budget exhausted: no forward passes left")
    cand = sys.argv[3]
    path = None if cand == "base" else os.path.abspath(cand)
    with H.device_lock():
        m = H.load(name, path)
        if op == "loss":
            x, y = H.windows(name, "probe", 64)
            tl = H.token_losses(m, x, y)
            T = tl.shape[1]
            q = [tl[:, a:b].mean().item() for a, b in [(0, T // 8), (T // 8, T // 2), (T // 2, T)]]
            flat_t, flat_l = y.reshape(-1), tl.reshape(-1)
            dec, _ = H.decoder(name)
            per = {}
            for t in torch.unique(flat_t):
                msk = flat_t == t
                per[int(t)] = (flat_l[msk].sum().item(), int(msk.sum()))
            worst = sorted(per.items(), key=lambda kv: -kv[1][0])[:12]
            res = {
                "loss": round(tl.mean().item(), 5),
                "loss_by_position": {
                    "first_eighth": round(q[0], 4),
                    "to_half": round(q[1], 4),
                    "second_half": round(q[2], 4),
                },
                "top_loss_targets": [
                    {"token": int(t), "text": dec([t]), "total_nats": round(s, 1), "count": c, "mean": round(s / c, 3)}
                    for t, (s, c) in worst
                ],
            }
        elif op == "sample":
            dec, enc = H.decoder(name)
            prompt = sys.argv[4] if len(sys.argv) > 4 else ""
            ids = enc(prompt) if prompt else [int(H.split_tokens(name, "probe")[0])]
            g = torch.Generator(device="cpu").manual_seed(0)
            idx = torch.tensor([ids], device=H.DEVICE)
            T = H.model_args(name)["block_size"]
            for _ in range(300):
                logits = m.lm_head(H.xb_forward(m, idx[:, -T:])[:, -1]).float().cpu() / 0.8
                nxt = torch.multinomial(torch.softmax(logits, -1), 1, generator=g)
                idx = torch.cat([idx, nxt.to(H.DEVICE)], 1)
            res = {"sample": dec(idx[0].tolist())}
        elif op == "acts":
            x, _ = H.windows(name, "probe", 8)
            hidden = []
            H.xb_forward(m, x.to(H.DEVICE), hidden)
            out = f"{H.HERE}/{name}/acts_{used(name) + 1}.npz"
            np.savez(out, tokens=x.numpy(), **{f"resid_{i}": h.numpy() for i, h in enumerate(hidden)})
            res = {"saved": out, "note": "resid_0 = embeddings, resid_i = after block i-1"}
        else:
            raise SystemExit(f"unknown op {op}")
    charge(name, op, cand, {k: v for k, v in res.items() if k in ("loss", "saved")})
    res["passes_left"] = H.BUDGET - used(name)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
