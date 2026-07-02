"""
Held-out BPC eval for r5 XL custom-vocab runs (byte-level BPE from tokenizer.json).

Core's eval (core/eval/eval.py) understands only char `stoi` (meta.pkl) or GPT-2
tiktoken. The r5 custom-vocab datasets ship a HF `tokenizer.json` and a meta.pkl of
{"vocab_size", "tokenizer"} (ADR-0012's meta.pkl seam, extended minimally). This
project-local wrapper reuses the exact same teacher-forced NLL / BPC computation as
core, swapping in the HF tokenizer resolved from meta.pkl. BPC stays comparable to
the whole series: total NLL / (character count of test.txt) / ln 2.

    uv run --with tokenizers python projects/shakespeare/eval_xl.py \
        projects/shakespeare/runs/r5-xl-bpe1k \
        --test projects/shakespeare/test.txt \
        --data-dir projects/shakespeare/data
"""
import argparse
import math
import os
import pickle

import torch

from nanogpt_core.model import GPT, GPTConfig


def main(out_dir, test_path, data_dir):
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    ckpt = torch.load(os.path.join(out_dir, "ckpt.pt"), map_location=device, weights_only=True)

    model = GPT(GPTConfig(**ckpt["model_args"]))
    sd = ckpt["model"]
    for k in list(sd):
        if k.startswith("_orig_mod."):
            sd[k[len("_orig_mod.") :]] = sd.pop(k)
    model.load_state_dict(sd)
    model.eval().to(device)

    block = ckpt["model_args"]["block_size"]
    dataset = ckpt.get("config", {}).get("dataset", "")
    meta_path = os.path.join(data_dir, dataset, "meta.pkl")
    meta = pickle.load(open(meta_path, "rb"))
    tok_path = os.path.join(data_dir, dataset, meta["tokenizer"])

    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(tok_path)

    text = open(test_path, encoding="utf-8").read()
    ids = tok.encode(text).ids
    nchars = len(text)  # BPC denominator: full char count (byte-level BPE is lossless)

    nll = 0.0
    ntok = 0
    with torch.no_grad():
        for i in range(0, len(ids) - 1, block):
            x = ids[i : i + block]
            y = ids[i + 1 : i + 1 + len(x)]
            x = x[: len(y)]
            if not y:
                break
            xb = torch.tensor([x], dtype=torch.long, device=device)
            yb = torch.tensor([y], dtype=torch.long, device=device)
            _, loss = model(xb, yb)
            nll += loss.item() * yb.numel()
            ntok += yb.numel()

    bpc = nll / nchars / math.log(2)
    tok_loss = nll / ntok
    nparams = sum(p.numel() for p in model.parameters())
    print(
        f"{out_dir}\ttokenizer=bpe{meta['vocab_size']}\tparams={nparams/1e6:.2f}M\t"
        f"tokens={ntok}\tchars={nchars}\t"
        f"token_loss={tok_loss:.4f}\tppl={math.exp(tok_loss):.2f}\tBPC={bpc:.4f}"
    )
    return {"out_dir": out_dir, "bpc": bpc, "token_loss": tok_loss, "params": nparams}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir")
    ap.add_argument("--test", required=True, dest="test_path")
    ap.add_argument("--data-dir", required=True, dest="data_dir")
    a = ap.parse_args()
    main(a.out_dir, a.test_path, a.data_dir)
