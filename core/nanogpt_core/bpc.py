"""Bits-per-character scoring — importable, so harnesses stop regex-scraping
the eval CLI's stdout (glyph's matrix_eval was parsing `BPC=([\\d.]+)` out of
a print line). core/eval/eval.py is now a thin shim over score_run().

BPC is the universal, tokenizer-agnostic metric: total negative
log-likelihood of the test text divided by its character count. Char-level
and BPE models produce different raw losses but are directly comparable in
BPC, so a whole series shares one yardstick. See ADR-0029.
"""
import math

import torch

from nanogpt_core.checkpoint import load_model, load_tokenizer


def score(model, tok, text, block_size, device):
    """Teacher-forced NLL over non-overlapping blocks → a result dict.

    The BPC denominator must cover exactly the characters the NLL scored:
    char models drop out-of-vocab characters from the ids, so those are
    excluded from nchars too (counting them would deflate BPC by a different
    amount per test text). Byte-level BPE and GPT-2 BPE are lossless, so
    their denominator is the full character count.
    """
    if tok.kind == "char":
        stoi = tok.meta["stoi"]
        ids = [stoi[c] for c in text if c in stoi]
        nchars, dropped = len(ids), len(text) - len(ids)
        label = "char"
    else:
        ids = tok.encode(text)
        nchars, dropped = len(text), 0
        label = f"bpe{tok.meta['vocab_size']}" if tok.kind == "bpe" else "gpt2-bpe"

    nll = 0.0
    ntok = 0
    with torch.no_grad():
        for i in range(0, len(ids) - 1, block_size):
            x = ids[i : i + block_size]
            y = ids[i + 1 : i + 1 + len(x)]
            x = x[: len(y)]
            if not y:
                break
            xb = torch.tensor([x], dtype=torch.long, device=device)
            yb = torch.tensor([y], dtype=torch.long, device=device)
            _, loss = model(xb, yb)
            nll += loss.item() * yb.numel()
            ntok += yb.numel()

    tok_loss = nll / ntok
    return {
        "tokenizer": label,
        "tokens": ntok,
        "chars": nchars,
        "dropped_chars": dropped,
        "token_loss": tok_loss,
        "ppl": math.exp(tok_loss),
        "bpc": nll / nchars / math.log(2),
    }


def score_run(out_dir, test_path, data_root="", device=None):
    """One call from run dir to result dict: load, resolve tokenizer, score."""
    model, ckpt = load_model(out_dir, device)
    tok = load_tokenizer(ckpt, data_root)
    with open(test_path, encoding="utf-8") as f:
        text = f.read()
    return score(model, tok, text, ckpt["model_args"]["block_size"], next(model.parameters()).device)
