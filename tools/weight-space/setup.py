"""Researcher-only. `setup` extracts base weights; `score <model> [cand]` scores on the TEST half."""

import json
import os
import sys
import torch
import harness as H


def setup():
    for name, (rel, _) in H.MODELS.items():
        d = f"{H.HERE}/{name}"
        os.makedirs(f"{d}/cands", exist_ok=True)
        c = torch.load(f"{rel}/ckpt.pt", map_location="cpu", weights_only=False)
        sd = {k.removeprefix("_orig_mod."): v.float() for k, v in c["model"].items()}
        sd.pop("transformer.wte.weight", None)  # tied to lm_head
        torch.save(sd, f"{d}/base.pt")
        json.dump(c["model_args"], open(f"{d}/model_args.json", "w"), indent=1)
        print(name, sum(v.numel() for v in sd.values()))


def score(name, cand=None):
    with H.device_lock():
        m = H.load(name, cand)
        x, y = H.windows(name, "test", 256)
        tl = H.token_losses(m, x, y)
    return tl.mean().item(), tl.mean(1).std().item() / (len(tl) ** 0.5)


if __name__ == "__main__":
    if sys.argv[1] == "setup":
        setup()
    else:
        loss, se = score(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print(json.dumps({"model": sys.argv[2], "test_loss": round(loss, 5), "se": round(se, 5)}))
