"""
Score this model on the fixed held-out test set in bits-per-character (BPC).

BPC is tokenizer-agnostic (total NLL of the test text / its character count), so
every model in the series — char-level or BPE — is directly comparable. The test
set is the series' single shared yardstick at research-lab/test.txt; pass a
different file as the first argument to score against something else.

Usage:  python eval.py [test_file]
"""
import os
import sys
import math
import pickle
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from model import GPTConfig, GPT  # this folder's architecture


def main(test_path=None):
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    ckpt = torch.load(os.path.join(HERE, "ckpt.pt"), map_location=device)

    model = GPT(GPTConfig(**ckpt["model_args"]))
    sd = ckpt["model"]
    for k in list(sd):
        if k.startswith("_orig_mod."):
            sd[k[len("_orig_mod.") :]] = sd.pop(k)
    model.load_state_dict(sd)
    model.eval().to(device)

    block = ckpt["model_args"]["block_size"]
    meta_path = os.path.join(HERE, "meta.pkl")
    # default: the canonical shared held-out test (two levels up: <repo>/research-lab/test.txt)
    repo = os.path.dirname(os.path.dirname(HERE))
    test_path = test_path or os.path.join(repo, "research-lab", "test.txt")
    text = open(test_path, encoding="utf-8").read()

    if os.path.exists(meta_path):
        stoi = pickle.load(open(meta_path, "rb"))["stoi"]
        ids = [stoi[c] for c in text if c in stoi]
        tokenizer = "char"
    else:
        import tiktoken

        ids = tiktoken.get_encoding("gpt2").encode(text)
        tokenizer = "gpt2-bpe"

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

    nchars = len(text)
    bpc = nll / nchars / math.log(2)
    tok_loss = nll / ntok
    print(
        f"{HERE}\t"
        f"tokenizer={tokenizer}\ttokens={ntok}\tchars={nchars}\t"
        f"token_loss={tok_loss:.4f}\tppl={math.exp(tok_loss):.2f}\tBPC={bpc:.4f}"
    )
    return {"tokenizer": tokenizer, "token_loss": tok_loss, "bpc": bpc}


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
