"""Sample passages from every sibling checkpoint, tagged by sampling seed.

Each run dir under --runs holding a ckpt.pt becomes one JSONL of --n passages
of --tokens tokens at --temp, generated in batches; every batch gets its own
torch seed (recorded per passage) so attribute.py can hold sampling seeds out.
Extra arms for the controls: --extra_temps samples the first sibling again at
other temperatures.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import torch

from nanogpt_core.model import GPT, GPTConfig

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "linewell"))
from compose import DEFAULT_MODEL_DIR, _find_tokenizer  # noqa: E402


def load(ckpt_path, device):
    ck = torch.load(ckpt_path, map_location=device, weights_only=True)
    conf = GPTConfig(**ck["model_args"])
    state = ck["model"]
    for k in list(state):
        if k.startswith("_orig_mod."):
            state[k[len("_orig_mod."):]] = state.pop(k)
    m = GPT(conf)
    m.load_state_dict(state)
    m.eval().to(device)
    val = ck.get("best_val_loss")
    return m, int(ck.get("iter_num", 0)), (float(val) if val is not None else None)


@torch.no_grad()
def sample_run(model, tok, n, tokens, temp, batch, base_seed, device, name, out_path):
    start = tok.encode("\n").ids
    with open(out_path, "w") as f:
        for b in range(0, n, batch):
            seed = base_seed + b // batch
            torch.manual_seed(seed)
            idx = torch.tensor([start] * min(batch, n - b), dtype=torch.long, device=device)
            out = model.generate(idx, tokens, temperature=temp, top_k=None)
            for row in out[:, len(start):].tolist():
                f.write(json.dumps({"run": name, "sample_seed": seed, "temp": temp, "ids": row,
                                    "text": tok.decode(row)}, ensure_ascii=False) + "\n")
    print(f"{name}: {n} passages -> {out_path}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True, help="dir of run dirs, each with ckpt.pt")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--tokens", type=int, default=256)
    ap.add_argument("--temp", type=float, default=0.8)
    ap.add_argument("--batch", type=int, default=100)
    ap.add_argument("--extra_temps", nargs="*", type=float, default=[0.6, 1.0])
    ap.add_argument("--model_dir", default=DEFAULT_MODEL_DIR, help="where the tokenizer.json lives")
    ap.add_argument("--device", default="mps")
    a = ap.parse_args()
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(_find_tokenizer(a.model_dir))
    os.makedirs(a.out, exist_ok=True)
    runs = sorted(d for d in glob.glob(os.path.join(a.runs, "*")) if os.path.exists(os.path.join(d, "ckpt.pt")))
    meta_path = os.path.join(a.out, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    for i, d in enumerate(runs):
        name = os.path.basename(d)
        model, it, val = load(os.path.join(d, "ckpt.pt"), a.device)
        meta[name] = {"iter_num": it, "best_val_loss": val}
        sample_run(model, tok, a.n, a.tokens, a.temp, a.batch, 1000 * (i + 1), a.device, name,
                   os.path.join(a.out, f"{name}.jsonl"))
        if i == 0:
            for t in a.extra_temps:
                sample_run(model, tok, a.n, a.tokens, t, a.batch, 1000 * (i + 1) + 500, a.device,
                           f"{name}-t{t}", os.path.join(a.out, f"{name}-t{t}.jsonl"))
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=1)


if __name__ == "__main__":
    main()
