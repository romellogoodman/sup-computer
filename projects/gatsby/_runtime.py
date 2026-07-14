"""
Shared runtime for gatsby's sample/eval scripts — thin wrappers over the core
loaders (nanogpt_core.checkpoint, ADR-0029). This file once carried its own
checkpoint-load + HF-tokenizer-resolve copies, following the seam
shakespeare's eval_xl.py established; core owns both now.

Run from the repo root (`tokenizers` is declared in the project's pyproject):
    uv run python projects/gatsby/sample.py ...
"""
import torch

from nanogpt_core import load_model, load_tokenizer, pick_device  # noqa: F401  (re-exported to the scripts)


def load_model_and_tokenizer(out_dir, data_dir, device):
    """Load a core GPT checkpoint + its byte-level BPE tokenizer."""
    model, ckpt = load_model(out_dir, device)
    return model, load_tokenizer(ckpt, data_dir)


def generate(model, tok, prime, max_new_tokens, device, seed, temperature=0.8, top_k=200):
    """Generate a continuation from a control-line prime. Returns the FULL decoded
    text (prime included); callers strip the prime themselves if they want only
    the continuation."""
    torch.manual_seed(seed)
    ids = tok.encode(prime)
    x = torch.tensor(ids, dtype=torch.long, device=device)[None, ...]
    with torch.no_grad():
        y = model.generate(x, max_new_tokens, temperature=temperature, top_k=top_k)
    return tok.decode(y[0].tolist())
