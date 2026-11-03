"""Weight-space editing harness: shared loader, probe/test split, budget ledger.

Probe half = first half of each release's val.bin (helpers may spend forward
passes on it). Test half = second half (only score.py touches it).
"""

import fcntl
import importlib.util
import json
import os
import pickle
from contextlib import contextmanager
import numpy as np
import torch

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# Working dir for base weights, candidates and ledgers (weights are gitignored).
HERE = os.environ.get("WSP_WORK", os.path.join(os.path.dirname(os.path.abspath(__file__)), "work"))
P = f"{REPO}/projects"
MODELS = {
    "shakespeare": (f"{P}/shakespeare/models/shakespeare-nanogpt-3", f"{P}/shakespeare/data/shakespeare_xl_bpe1k"),
    "gatsby": (f"{P}/gatsby/models/gatsby-nanogpt-3", f"{P}/gatsby/models/gatsby-nanogpt-3/data"),
    "kenosha": (f"{P}/kenosha-kid/models/kenosha-kid-nanogpt-2", f"{P}/kenosha-kid/data/kenosha-drift-r1"),
    "daydream": (
        f"{P}/daydream/models/daydream-chess-nanogpt-1",
        f"{P}/daydream/models/daydream-chess-nanogpt-1/regular",
    ),
    "glyph": (f"{P}/glyph/models/glyph-nanogpt-1", f"{P}/glyph/data/omni"),
    "pona": (f"{P}/pona/models/pona-nanogpt-1", f"{P}/pona/data/tokenized-chat"),
}
BUDGET = 50
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
torch.set_grad_enabled(False)


def _model_module(name):
    rel = MODELS[name][0]
    spec = importlib.util.spec_from_file_location(f"wsp_model_{name}", f"{rel}/model.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def model_args(name):
    p = f"{HERE}/{name}/model_args.json"
    return json.load(open(p))


def load(name, state_path=None):
    """Build the model with base weights, or a candidate state_dict (.pt of tensors)."""
    mod = _model_module(name)
    args = dict(model_args(name))
    args["dropout"] = 0.0
    import io
    import contextlib

    with contextlib.redirect_stdout(io.StringIO()):
        m = mod.GPT(mod.GPTConfig(**args))
    sd = torch.load(state_path or f"{HERE}/{name}/base.pt", map_location="cpu")
    missing, unexpected = m.load_state_dict(sd, strict=False)
    missing = [k for k in missing if k != "transformer.wte.weight" and k != "lm_head.weight"]
    if missing or unexpected:
        raise SystemExit(f"state_dict mismatch: missing={missing} unexpected={unexpected}")
    m.transformer.wte.weight = m.lm_head.weight
    return m.to(DEVICE).eval()


def split_tokens(name, which):
    data = np.memmap(f"{MODELS[name][1]}/val.bin", dtype=np.uint16, mode="r")
    h = len(data) // 2
    return np.asarray(data[:h] if which == "probe" else data[h:])


def windows(name, which, n):
    toks = split_tokens(name, which)
    T = model_args(name)["block_size"]
    starts = np.linspace(0, len(toks) - T - 1, n).astype(np.int64)
    x = np.stack([toks[s : s + T] for s in starts]).astype(np.int64)
    y = np.stack([toks[s + 1 : s + T + 1] for s in starts]).astype(np.int64)
    return torch.from_numpy(x), torch.from_numpy(y)


def token_losses(m, x, y, bs=8):
    out = []
    for i in range(0, len(x), bs):
        xb, yb = x[i : i + bs].to(DEVICE), y[i : i + bs].to(DEVICE)
        h = xb_forward(m, xb)
        logits = m.lm_head(h).float()
        out.append(
            torch.nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), yb.view(-1), reduction="none")
            .view(yb.shape)
            .cpu()
        )
    return torch.cat(out)


def xb_forward(m, xb, hidden=None):
    x = m.transformer.wte(xb)
    if hidden is not None:
        hidden.append(x.float().cpu())
    for blk in m.transformer.h:
        x = blk(x)
        if hidden is not None:
            hidden.append(x.float().cpu())
    return m.transformer.ln_f(x)


@contextmanager
def device_lock():
    with open(f"{HERE}/.device.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def decoder(name):
    rel, data = MODELS[name]
    tj = next(
        (
            p
            for p in [
                f"{data}/tokenizer.json",
                f"{rel}/data/tokenizer.json",
                f"{rel}/shakespeare_xl_bpe1k/tokenizer.json",
            ]
            if os.path.exists(p)
        ),
        None,
    )
    if tj:
        from tokenizers import Tokenizer

        tok = Tokenizer.from_file(tj)
        return lambda ids: tok.decode(ids), lambda s: tok.encode(s).ids
    meta = pickle.load(open(f"{data}/meta.pkl", "rb"))
    itos, stoi = meta["itos"], meta["stoi"]
    sep = " " if name == "pona" else ""
    enc = (
        (lambda s: [stoi[w] for w in s.split() if w in stoi])
        if name == "pona"
        else (lambda s: [stoi[c] for c in s if c in stoi])
    )
    return lambda ids: sep.join(str(itos[i]) for i in ids), enc
