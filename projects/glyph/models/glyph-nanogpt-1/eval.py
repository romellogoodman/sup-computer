"""
Score a trained checkpoint on a fixed held-out test set, in bits-per-character.

BPC is the universal, tokenizer-agnostic metric: total negative log-likelihood
of the test text divided by its character count. Char-level and BPE models
produce different raw losses but are directly comparable in BPC, so a whole
series shares one yardstick.

This scores the CURRENT (modern: RoPE + RMSNorm + bias-free) architecture only.
Historical base-architecture versions are scored inside their own frozen
projects/<project>/models/<version>/ folder, which vendors its own model.py.

Usage:
  python core/eval/eval.py <out_dir> \
      --test projects/shakespeare/test.txt \
      --data-dir projects/shakespeare/data        # for char models' meta.pkl
"""
import argparse
import math
import os
import pickle

import torch

from model import GPTConfig, GPT  # vendored: no cross-folder imports in a frozen release


def main(out_dir, test_path, data_dir=""):
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
    meta_path = os.path.join(data_dir, dataset, "meta.pkl") if data_dir else ""
    text = open(test_path, encoding="utf-8").read()

    if meta_path and os.path.exists(meta_path):
        stoi = pickle.load(open(meta_path, "rb"))["stoi"]
        ids = [stoi[c] for c in text if c in stoi]
        tokenizer = "char"
        # BPC's denominator must cover exactly the characters the NLL scored.
        # OOV characters are dropped from ids, so counting them in nchars would
        # deflate BPC — and by a different amount per test text.
        nchars = len(ids)
        dropped = len(text) - len(ids)
        if dropped:
            print(f"warning: {dropped} chars not in vocab, excluded from BPC")
    else:
        import tiktoken

        ids = tiktoken.get_encoding("gpt2").encode(text)
        tokenizer = "gpt2-bpe"
        nchars = len(text)

    # teacher-forced NLL over non-overlapping blocks
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
    print(
        f"{out_dir}\t"
        f"tokenizer={tokenizer}\ttokens={ntok}\tchars={nchars}\t"
        f"token_loss={tok_loss:.4f}\tppl={math.exp(tok_loss):.2f}\tBPC={bpc:.4f}"
    )
    return {"out_dir": out_dir, "tokenizer": tokenizer, "token_loss": tok_loss, "bpc": bpc}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("out_dir", help="run dir containing ckpt.pt")
    ap.add_argument("--test", required=True, dest="test_path", help="held-out test text")
    ap.add_argument(
        "--data-dir",
        default="",
        dest="data_dir",
        help="parent dir of <dataset>/meta.pkl (char models); omit for BPE",
    )
    a = ap.parse_args()
    main(a.out_dir, a.test_path, a.data_dir)
