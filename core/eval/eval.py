"""
Score a trained checkpoint on the fixed held-out test set (research-lab/test.txt).

Reports bits-per-character (BPC) as the universal, tokenizer-agnostic metric:
total negative log-likelihood of the test text divided by its character count.
Char-level and BPE models produce different raw losses but are directly
comparable in BPC, so the whole leaderboard shares one yardstick.

Usage:  python research-lab/eval.py <out_dir> [test_file]
"""
import os
import sys
import math
import pickle
import torch

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "research-lab"))  # import model.py / model_modern.py (both live here)


def load_arch(out_dir):
    """Pick the right GPT class for this checkpoint's architecture."""
    tag = ""
    af = os.path.join(out_dir, "arch.txt")
    if os.path.exists(af):
        tag = open(af).read().strip()
    if tag == "modern":
        from model_modern import GPTConfig, GPT
    else:
        from model import GPTConfig, GPT
    return GPTConfig, GPT


def main(out_dir, test_path=None):
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    ckpt = torch.load(os.path.join(out_dir, "ckpt.pt"), map_location=device)

    GPTConfig, GPT = load_arch(out_dir)
    model = GPT(GPTConfig(**ckpt["model_args"]))
    sd = ckpt["model"]
    for k in list(sd):
        if k.startswith("_orig_mod."):
            sd[k[len("_orig_mod.") :]] = sd.pop(k)
    model.load_state_dict(sd)
    model.eval().to(device)

    block = ckpt["model_args"]["block_size"]
    dataset = ckpt.get("config", {}).get("dataset", "")
    meta_path = os.path.join(REPO, "research-lab", "data", dataset, "meta.pkl")
    test_path = test_path or os.path.join(REPO, "research-lab", "test.txt")
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
        f"{out_dir}\t"
        f"tokenizer={tokenizer}\ttokens={ntok}\tchars={nchars}\t"
        f"token_loss={tok_loss:.4f}\tppl={math.exp(tok_loss):.2f}\tBPC={bpc:.4f}"
    )
    return {"out_dir": out_dir, "tokenizer": tokenizer, "token_loss": tok_loss, "bpc": bpc}


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
