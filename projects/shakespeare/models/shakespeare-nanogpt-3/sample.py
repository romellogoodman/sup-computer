"""
Sample from the trained v3 model (byte-level BPE from tokenizer.json).

Mirrors core/nanogpt_core/sample.py but resolves the HF tokenizer from the local
dataset's meta.pkl {"tokenizer": "tokenizer.json"} seam (ADR-0012) instead of
char stoi / GPT-2 tiktoken. Runs in place from this folder against ./ckpt.pt.

Requires the Hugging Face `tokenizers` library — run it as:

    uv run --with tokenizers python sample.py --start="ROMEO:" --num_samples=1 --max_new_tokens=500
"""
import argparse
import os
import pickle

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, HERE)
from model import GPTConfig, GPT  # this folder's architecture


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="\n")
    ap.add_argument("--num_samples", type=int, default=1)
    ap.add_argument("--max_new_tokens", type=int, default=500)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top_k", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1337)
    a = ap.parse_args()

    torch.manual_seed(a.seed)
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    ckpt = torch.load(os.path.join(HERE, "ckpt.pt"), map_location=device, weights_only=False)
    model = GPT(GPTConfig(**ckpt["model_args"]))
    sd = ckpt["model"]
    for k in list(sd):
        if k.startswith("_orig_mod."):
            sd[k[len("_orig_mod.") :]] = sd.pop(k)
    model.load_state_dict(sd)
    model.eval().to(device)

    dataset = ckpt.get("config", {}).get("dataset", "shakespeare_xl_bpe1k")
    data_dir = os.path.join(HERE, dataset)
    meta = pickle.load(open(os.path.join(data_dir, "meta.pkl"), "rb"))
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(os.path.join(data_dir, meta["tokenizer"]))

    start_ids = tok.encode(a.start).ids
    x = torch.tensor(start_ids, dtype=torch.long, device=device)[None, ...]
    with torch.no_grad():
        for _ in range(a.num_samples):
            y = model.generate(x, a.max_new_tokens, temperature=a.temperature, top_k=a.top_k)
            print(tok.decode(y[0].tolist()))
            print("---------------")


if __name__ == "__main__":
    main()
