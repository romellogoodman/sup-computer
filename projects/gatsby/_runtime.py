"""
Shared runtime for gatsby's core-riding, BPE-aware sample/eval scripts.

Gatsby migrated onto the shared `core` engine with byte-level BPE (docs/adr/0023).
Core's own sample.py/eval.py understand only char `stoi` (meta.pkl) or GPT-2
tiktoken, so — following the seam shakespeare's eval_xl.py/sample_xl.py
established (ADR-0012) — the project-local scripts load core's GPT and resolve
the HF tokenizer from the dataset's meta.pkl {"tokenizer": "tokenizer.json"}.

Run from the repo root (`tokenizers` is declared in the project's pyproject):
    uv run python projects/gatsby/sample.py ...
"""
import os
import pickle

import torch

from nanogpt_core.model import GPT, GPTConfig


def pick_device(pref=None):
    if pref:
        return pref
    return "mps" if torch.backends.mps.is_available() else "cpu"


def load_model_and_tokenizer(out_dir, data_dir, device):
    """Load a core GPT checkpoint + its byte-level BPE tokenizer.

    out_dir  : run dir holding ckpt.pt
    data_dir : the data_root (e.g. projects/gatsby/data); the dataset name and
               tokenizer filename are read from the checkpoint config + meta.pkl.
    """
    from tokenizers import Tokenizer

    ckpt = torch.load(os.path.join(out_dir, "ckpt.pt"), map_location=device, weights_only=True)
    model = GPT(GPTConfig(**ckpt["model_args"]))
    sd = ckpt["model"]
    for k in list(sd):
        if k.startswith("_orig_mod."):
            sd[k[len("_orig_mod."):]] = sd.pop(k)
    model.load_state_dict(sd)
    model.eval().to(device)

    dataset = ckpt.get("config", {}).get("dataset", "")
    meta = pickle.load(open(os.path.join(data_dir, dataset, "meta.pkl"), "rb"))
    tok = Tokenizer.from_file(os.path.join(data_dir, dataset, meta["tokenizer"]))
    return model, tok


def generate(model, tok, prime, max_new_tokens, device, seed, temperature=0.8, top_k=200):
    """Generate a continuation from a control-line prime. Returns the FULL decoded
    text (prime included); callers strip the prime themselves if they want only
    the continuation."""
    torch.manual_seed(seed)
    ids = tok.encode(prime).ids
    x = torch.tensor(ids, dtype=torch.long, device=device)[None, ...]
    with torch.no_grad():
        y = model.generate(x, max_new_tokens, temperature=temperature, top_k=top_k)
    return tok.decode(y[0].tolist())
