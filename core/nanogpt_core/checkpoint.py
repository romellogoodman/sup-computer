"""Checkpoint + tokenizer loading — the library surface projects import.

Before this module existed the load ritual (torch.load → GPTConfig →
strip compile/DDP prefixes → eval().to(device)) was copy-pasted at ten
sites across the workspace and had already drifted (one site used
weights_only=False, only one stripped the DDP prefix). Project harnesses
import these instead of re-pasting the block. See ADR-0029.

Frozen releases under projects/*/models/<version>/ do NOT use this — they
carry their own snapshot (ADR-0003).
"""
import os
import pickle

import torch

from nanogpt_core.model import GPT, GPTConfig

# torch.compile wraps the module in _orig_mod.; DDP wraps it in module. —
# a checkpoint saved from a wrapped model carries the prefix on every key.
_WRAPPER_PREFIXES = ("_orig_mod.", "module.")


def pick_device(pref=None):
    """The studio device policy: an explicit preference wins, otherwise
    cuda > mps > cpu."""
    if pref:
        return pref
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_model(out_dir, device=None):
    """Load <out_dir>/ckpt.pt (or a direct .pt path) → (model, checkpoint).

    The model comes back eval()'d on the picked device; the raw checkpoint
    dict is returned alongside for its model_args / config / iter_num.
    """
    device = pick_device(device)
    path = out_dir if str(out_dir).endswith(".pt") else os.path.join(out_dir, "ckpt.pt")
    ckpt = torch.load(path, map_location=device, weights_only=True)
    model = GPT(GPTConfig(**ckpt["model_args"]))
    sd = ckpt["model"]
    for k in list(sd):
        stripped = k
        for prefix in _WRAPPER_PREFIXES:
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix):]
        if stripped != k:
            sd[stripped] = sd.pop(k)
    model.load_state_dict(sd)
    model.eval().to(device)
    return model, ckpt


class Tokenizer:
    """Uniform encode/decode over the meta.pkl shapes (ADR-0012).

    kind is "char", "bpe" (corpus-trained HF tokenizer.json), or "gpt2-bpe";
    meta is the raw meta.pkl dict where one existed.
    """

    def __init__(self, kind, encode, decode, meta=None):
        self.kind = kind
        self.encode = encode
        self.decode = decode
        self.meta = meta or {}


def load_tokenizer(ckpt, data_root=""):
    """Resolve a checkpoint's tokenizer from <data_root>/<dataset>/meta.pkl.

    Three shapes, in order: {"tokenizer": "tokenizer.json"} (the HF seam
    ADR-0012 grew for corpus-trained BPE — shakespeare r5 established it,
    gatsby's ADR-0023 migration made it permanent), char stoi/itos, and no
    meta at all → GPT-2 tiktoken. Char encoding is strict: an out-of-vocab
    prompt character raises rather than silently vanishing (BPC scoring
    handles OOV itself — see nanogpt_core.bpc).
    """
    dataset = ckpt.get("config", {}).get("dataset", "")
    meta_path = os.path.join(data_root, dataset, "meta.pkl") if data_root else ""
    if meta_path and os.path.exists(meta_path):
        with open(meta_path, "rb") as f:
            meta = pickle.load(f)
        if "tokenizer" in meta:
            from tokenizers import Tokenizer as HFTokenizer  # core's `hf` extra

            tok = HFTokenizer.from_file(os.path.join(data_root, dataset, meta["tokenizer"]))
            return Tokenizer("bpe", lambda s: tok.encode(s).ids, tok.decode, meta)
        stoi, itos = meta["stoi"], meta["itos"]
        return Tokenizer(
            "char",
            lambda s: [stoi[c] for c in s],
            lambda ids: "".join(itos[i] for i in ids),
            meta,
        )
    import tiktoken

    enc = tiktoken.get_encoding("gpt2")
    return Tokenizer(
        "gpt2-bpe",
        lambda s: enc.encode(s, allowed_special={"<|endoftext|>"}),
        enc.decode,
    )
