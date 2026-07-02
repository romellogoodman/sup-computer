"""
Sample from an r5 XL custom-vocab run (byte-level BPE from tokenizer.json).

Mirrors core/nanogpt_core/sample.py but resolves the HF tokenizer from the dataset's
meta.pkl {"tokenizer": "tokenizer.json"} instead of char stoi / GPT-2 tiktoken.

    uv run --with tokenizers python projects/shakespeare/sample_xl.py \
        --out_dir projects/shakespeare/runs/r5-xl-bpe1k \
        --data-dir projects/shakespeare/data \
        --start "ROMEO:" --num_samples 1 --max_new_tokens 500 --temperature 0.8
"""
import argparse
import os
import pickle

import torch

from nanogpt_core.model import GPT, GPTConfig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--data-dir", required=True, dest="data_dir")
    ap.add_argument("--start", default="\n")
    ap.add_argument("--num_samples", type=int, default=1)
    ap.add_argument("--max_new_tokens", type=int, default=500)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top_k", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1337)
    a = ap.parse_args()

    torch.manual_seed(a.seed)
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    ckpt = torch.load(os.path.join(a.out_dir, "ckpt.pt"), map_location=device, weights_only=True)
    model = GPT(GPTConfig(**ckpt["model_args"]))
    sd = ckpt["model"]
    for k in list(sd):
        if k.startswith("_orig_mod."):
            sd[k[len("_orig_mod.") :]] = sd.pop(k)
    model.load_state_dict(sd)
    model.eval().to(device)

    dataset = ckpt.get("config", {}).get("dataset", "")
    meta = pickle.load(open(os.path.join(a.data_dir, dataset, "meta.pkl"), "rb"))
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(os.path.join(a.data_dir, dataset, meta["tokenizer"]))

    start_ids = tok.encode(a.start).ids
    x = torch.tensor(start_ids, dtype=torch.long, device=device)[None, ...]
    with torch.no_grad():
        for _ in range(a.num_samples):
            y = model.generate(x, a.max_new_tokens, temperature=a.temperature, top_k=a.top_k)
            print(tok.decode(y[0].tolist()))
            print("---------------")


if __name__ == "__main__":
    main()
