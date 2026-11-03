"""Researcher-only: paired held-out comparison of base vs final for each model."""

import json
import os
import sys
import torch
import harness as H


def perwin(name, cand):
    with H.device_lock():
        m = H.load(name, cand)
        x, y = H.windows(name, "test", 256)
        return H.token_losses(m, x, y).mean(1)


rows = []
for name in sys.argv[1:] or H.MODELS:
    f = f"{H.HERE}/{name}/final.pt"
    if not os.path.exists(f):
        rows.append({"model": name, "status": "no final.pt"})
        continue
    b, c = perwin(name, None), perwin(name, f)
    d = c - b
    base = torch.load(f"{H.HERE}/{name}/base.pt")
    fin = torch.load(f)
    changed = sum(int((base[k] != fin[k]).sum()) for k in base)
    total = sum(v.numel() for v in base.values())
    rows.append(
        {
            "model": name,
            "base": round(b.mean().item(), 5),
            "final": round(c.mean().item(), 5),
            "delta": round(d.mean().item(), 5),
            "se": round(d.std().item() / len(d) ** 0.5, 5),
            "windows_better": int((d < 0).sum()),
            "changed_weights": changed,
            "changed_pct": round(100 * changed / total, 4),
            "passes_used": sum(1 for _ in open(f"{H.HERE}/{name}/ledger.jsonl"))
            if os.path.exists(f"{H.HERE}/{name}/ledger.jsonl")
            else 0,
        }
    )
for r in rows:
    print(json.dumps(r))
