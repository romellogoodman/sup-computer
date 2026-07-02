"""
Score this model on the fixed held-out test set in bits-per-character (BPC).

BPC is tokenizer-agnostic (total NLL of the test text / its character count), so
every model in the series — char-level, GPT-2 BPE, or this custom 1024-vocab
byte-level BPE — is directly comparable. The test set is the series' single
shared yardstick: projects/shakespeare/test.txt (two levels up); pass a different
file as the first argument to score against something else.

This is a byte-level-BPE-aware eval: it resolves the HF tokenizer from the local
meta.pkl {"tokenizer": "tokenizer.json"} seam (ADR-0012) instead of char stoi /
GPT-2 tiktoken. The NLL/BPC computation is identical to core/eval/eval.py.

Requires the Hugging Face `tokenizers` library — run it as:

    uv run --with tokenizers python eval.py [test_file]
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
    ckpt = torch.load(os.path.join(HERE, "ckpt.pt"), map_location=device, weights_only=False)

    model = GPT(GPTConfig(**ckpt["model_args"]))
    sd = ckpt["model"]
    for k in list(sd):
        if k.startswith("_orig_mod."):
            sd[k[len("_orig_mod.") :]] = sd.pop(k)
    model.load_state_dict(sd)
    model.eval().to(device)

    block = ckpt["model_args"]["block_size"]

    # tokenizer: resolve from this run's dataset meta.pkl (the ADR-0012 seam)
    dataset = ckpt.get("config", {}).get("dataset", "shakespeare_xl_bpe1k")
    data_dir = os.path.join(HERE, dataset)
    meta = pickle.load(open(os.path.join(data_dir, "meta.pkl"), "rb"))
    tok_path = os.path.join(data_dir, meta["tokenizer"])
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(tok_path)

    # default: the shared held-out test at the project root (two levels up)
    test_path = test_path or os.path.join(os.path.dirname(os.path.dirname(HERE)), "test.txt")
    text = open(test_path, encoding="utf-8").read()
    ids = tok.encode(text).ids
    nchars = len(text)  # BPC denominator: full char count (byte-level BPE is lossless)

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
    nparams = sum(p.numel() for p in model.parameters())
    print(
        f"{HERE}\ttokenizer=bpe{meta['vocab_size']}\tparams={nparams/1e6:.2f}M\t"
        f"tokens={ntok}\tchars={nchars}\t"
        f"token_loss={tok_loss:.4f}\tppl={math.exp(tok_loss):.2f}\tBPC={bpc:.4f}"
    )
    return {"tokenizer": f"bpe{meta['vocab_size']}", "token_loss": tok_loss, "bpc": bpc, "params": nparams}


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
