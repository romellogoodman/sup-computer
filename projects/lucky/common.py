"""common.py -- the two games: tokens, floors, examples, and the scorer.

Everything here is shared by train.py, evaluate.py and harness.py, so the
rule "k is enforced in three places" (loader, harness, block_size) has one
definition to read.

A draw is a fixed-length row of tokens, one token per number:

  pick3      d d d \\n                 4 tokens   vocab: 0-9, \\n          (11)
  powerball  w w w w w | r \\n         8 tokens   vocab: 1-69, |, \\n      (71)

An example is "the last k draws -> the next draw", cut at draw boundaries.
A newline leads the window, so the first token of the first draw has
something to follow. The loss covers only the final draw, so the history
version and the no-history control (k = 0) are trained on exactly the same
targets and differ only in what they can read.

  block_size = (k + 1) * tokens_per_draw     pick3: 36 / 4   powerball: 72 / 8
"""

import itertools
import math
import os
import pickle

import numpy as np
import torch

K_HISTORY = 8  # the history version reads the last 8 draws; the control reads none

GAMES = {
    "pick3": {
        "tokens_per_draw": 4,
        "vocab": [str(d) for d in range(10)] + ["\n"],
        "outcomes": 1000,
        "arm": "char",
    },
    "powerball": {
        "tokens_per_draw": 8,
        "vocab": [str(n) for n in range(1, 70)] + ["|", "\n"],
        "outcomes": math.comb(69, 5) * 26,  # 292,201,338
        "arm": "number",
    },
}
for _g in GAMES.values():
    _g["floor_bits"] = math.log2(_g["outcomes"])
    _g["stoi"] = {t: i for i, t in enumerate(_g["vocab"])}
    _g["newline"] = _g["stoi"]["\n"]

SEP = GAMES["powerball"]["stoi"]["|"]  # 69
# all 120 orderings of five white slots, for the set-level score
PERMS = torch.tensor(list(itertools.permutations(range(5))), dtype=torch.long)


def floor_bits(game):
    return GAMES[game]["floor_bits"]


def block_size(game, history):
    return (history + 1) * GAMES[game]["tokens_per_draw"]


def encode_draw(game, draw):
    """pick3: '407' -> [4,0,7,NL].  powerball: ([w1..w5], red) -> [w.., SEP, red, NL]."""
    g = GAMES[game]
    if game == "pick3":
        return [int(c) for c in draw] + [g["newline"]]
    whites, red = draw
    return [w - 1 for w in whites] + [SEP, red - 1, g["newline"]]


def load_dataset(data_dir):
    """-> (draws [N, T] int64 tensor in time order, meta dict)."""
    with open(os.path.join(data_dir, "meta.pkl"), "rb") as f:
        meta = pickle.load(f)
    draws = np.fromfile(os.path.join(data_dir, "draws.bin"), dtype=np.uint16)
    draws = torch.from_numpy(draws.astype(np.int64)).view(-1, meta["tokens_per_draw"])
    return draws, meta


def shuffle_whites(rows, generator):
    """rows [..., 8] powerball draws -> the same draws, whites in a fresh random order."""
    order = torch.rand(rows.shape[:-1] + (5,), generator=generator).argsort(-1)
    out = rows.clone()
    out[..., :5] = torch.gather(rows[..., :5], -1, order)
    return out


def windows(draws, idx, history):
    """Rows of consecutive draws ending at each target index: [B, history+1, T]."""
    offsets = torch.arange(-history, 1)
    return draws[idx[:, None] + offsets[None, :]]


def to_xy(game, win):
    """[B, history+1, T] draws -> (x, y) with the loss masked to the final draw."""
    g = GAMES[game]
    b = win.shape[0]
    flat = win.reshape(b, -1)
    lead = torch.full((b, 1), g["newline"], dtype=torch.long)
    seq = torch.cat([lead, flat], dim=1)
    x, y = seq[:, :-1], seq[:, 1:].clone()
    y[:, : -g["tokens_per_draw"]] = -1
    return x, y


@torch.no_grad()
def bits_per_draw(model, game, draws, idx, history, device, batch=1024):
    """Exact held-out score, in bits, for each target draw in idx.

    pick3: -log2 P(d d d \\n | history).
    powerball: set level. The model's probability is summed over all 120
    orderings of the target draw's whites, so the number compares to the
    28.12-bit set floor and not the 35.0-bit sequence floor. History draws
    are read in published (sorted) order.
    """
    g = GAMES[game]
    t = g["tokens_per_draw"]
    model.eval()
    out = []
    per = max(1, batch // (120 if game == "powerball" else 1))
    for s in range(0, len(idx), per):
        win = windows(draws, idx[s:s + per], history)  # [b, h+1, T]
        b = win.shape[0]
        if game == "powerball":
            win = win[:, None].repeat(1, 120, 1, 1)  # [b, 120, h+1, T]
            target_whites = win[:, :, -1, :5]
            win[:, :, -1, :5] = torch.gather(target_whites, -1, PERMS[None].expand(b, -1, -1))
            win = win.reshape(b * 120, history + 1, t)
        x, y = to_xy(game, win)
        logits, _ = model(x.to(device), y.to(device))
        logp = torch.log_softmax(logits[:, -t:, :].float(), dim=-1)
        tgt = y[:, -t:].to(device)
        seq_logp = logp.gather(-1, tgt[..., None]).squeeze(-1).sum(-1)  # nats, per sequence
        if game == "powerball":
            seq_logp = torch.logsumexp(seq_logp.view(b, 120), dim=1)
        out.append((-seq_logp / math.log(2)).cpu())
    return torch.cat(out)
