"""harness.py -- the pick harness: the model picks numbers, the harness makes the ticket.

The harness owns the ticket's form and never touches its numbers:

  shape   it asks for exactly five whites, writes the separator itself, asks
          for one red, and writes the end. (Pick 3: it asks for three digits.)
  order   it sorts the five whites after they are picked.

The model owns the numbers, unmasked, sampled at temperature 1 from a seed:

  white range   1-69            a miss is a reject
  red range     1-26            a miss is a reject
  no repeats    among whites    a miss is a reject (the red may match a white)

A lottery terminal will not sell an invalid ticket, so the played ticket is
the first valid attempt: attempt n uses seed + n, and the rejects before it
are kept and printed, not thrown away. The same (weights, tape, seed) always
gives the same ticket.

The tape is the prompt: the last 8 real draws, frozen at the end of the
corpus. The no-history control has no tape.

Run inside this folder, after prepare.py and train.py:

  python harness.py pick                  # one pick from the frozen tape
  python harness.py pick --draws 5        # roll forward: each pick joins the tape
  python harness.py rate --n 1000000      # raw valid-ticket rate + the memorization check
"""

import argparse
import csv
import json
import math
import os
import sys

import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from model import GPT, GPTConfig  # noqa: E402

from common import GAMES, SEP, K_HISTORY, encode_draw, load_dataset  # noqa: E402

def load_model(path, device):
    """This folder's own loader: ckpt.pt -> (model in eval mode, checkpoint dict)."""
    ckpt = torch.load(path, map_location=device, weights_only=True)
    model = GPT(GPTConfig(**ckpt["model_args"]))
    model.load_state_dict(ckpt["model"])
    model.eval().to(device)
    return model, ckpt


MAX_ATTEMPTS = 100          # a pick gives up after this many rejects in a row
SEED_STRIDE = 1000          # rolled-forward draw j starts at seed + j * SEED_STRIDE


class Picker:
    def __init__(self, ckpt, device="cpu"):
        path = ckpt if ckpt.endswith(".pt") else os.path.join(ckpt, "ckpt.pt")
        self.model, self.ckpt = load_model(path, device)
        self.device = device
        cfg = self.ckpt["config"]
        self.game = cfg["game"]
        self.history = cfg["history"]
        self.g = GAMES[self.game]
        self.data_dir = HERE  # draws.bin, meta.pkl and draws.csv sit beside this file
        self.draws, self.meta = load_dataset(self.data_dir)
        self.n_slots = 3 if self.game == "pick3" else 6

    # --- the tape -----------------------------------------------------------
    def frozen_tape(self):
        """The last 8 draws in the corpus, as token rows. Empty for the control."""
        return self.draws[len(self.draws) - self.history:] if self.history else self.draws[:0]

    def context(self, tape):
        """Token rows -> the prompt: a leading newline, then the tape."""
        lead = torch.tensor([self.g["newline"]], dtype=torch.long)
        return torch.cat([lead, tape.reshape(-1)])

    # --- raw sampling -------------------------------------------------------
    @torch.no_grad()
    def sample_raw(self, contexts, generator):
        """contexts [B, L] -> raw picks [B, n_slots] of token ids, unmasked.

        Powerball: five white slots, then the harness writes the separator,
        then one red slot. Whatever token the model emits in a slot stays in
        its context for the next slot, valid or not.
        """
        return self.sample_raw_shared(contexts, torch.arange(contexts.shape[0]), generator)

    @torch.no_grad()
    def sample_raw_shared(self, contexts, which, generator):
        """Like sample_raw, but many samples may share a context: sample i
        continues contexts[which[i]]. Each distinct context is read once and
        its attention keys and values are cached, so a million samples over
        143 tapes cost a million six-token continuations, not a million
        re-reads of the tape. Same numbers as the plain forward pass."""
        logits, cache = self._step(contexts.to(self.device), 0, None)
        which = which.to(self.device)
        logits = logits[which]
        cache = [(k[which], v[which]) for k, v in cache]
        pos = contexts.shape[1]
        picks = []
        for slot in range(self.n_slots):
            probs = torch.softmax(logits.float(), dim=-1).cpu()
            tok = torch.multinomial(probs, 1, generator=generator)
            picks.append(tok)
            if slot == self.n_slots - 1:
                break
            logits, cache = self._step(tok.to(self.device), pos, cache)
            pos += 1
            if self.game == "powerball" and slot == 4:  # the harness writes the separator
                sep = torch.full((tok.shape[0], 1), SEP, dtype=torch.long, device=self.device)
                logits, cache = self._step(sep, pos, cache)
                pos += 1
        return torch.cat(picks, dim=1)

    def _step(self, tokens, pos, cache):
        """Run tokens [B, T] sitting at positions pos.. through the model.
        cache is None (a fresh context, T tokens, causal) or the per-layer
        (keys, values) so far (then T must be 1). -> (last-position logits,
        cache extended by these tokens)."""
        m = self.model
        x = m.transformer.wte(tokens)
        b, t, c = x.shape
        assert cache is None or t == 1
        out = []
        for i, blk in enumerate(m.transformer.h):
            a = blk.attn
            q, k, v = a.c_attn(blk.ln_1(x)).split(c, dim=2)
            q, k, v = (z.view(b, t, a.n_head, a.head_dim).transpose(1, 2) for z in (q, k, v))
            cos = a.rope_cos[pos:pos + t].view(1, 1, t, a.head_dim // 2)
            sin = a.rope_sin[pos:pos + t].view(1, 1, t, a.head_dim // 2)

            def rope(z):
                z1, z2 = z[..., 0::2], z[..., 1::2]
                return torch.stack((z1 * cos - z2 * sin, z1 * sin + z2 * cos), dim=-1).flatten(-2)
            q, k = rope(q), rope(k)
            if cache is not None:
                k = torch.cat([cache[i][0], k], dim=2)
                v = torch.cat([cache[i][1], v], dim=2)
            y = F.scaled_dot_product_attention(q, k, v, is_causal=cache is None and t > 1)
            x = x + a.c_proj(y.transpose(1, 2).contiguous().view(b, t, c))
            x = x + blk.mlp(blk.ln_2(x))
            out.append((k, v))
        return m.lm_head(m.transformer.ln_f(x[:, -1, :])), out

    def judge(self, picks):
        """picks [B, n_slots] -> dict of boolean masks, one per rule."""
        if self.game == "pick3":
            ok = (picks < 10).all(1)
            return {"valid": ok, "not_a_digit": ~ok}
        whites, red = picks[:, :5], picks[:, 5]
        white_range = (whites < 69).all(1)
        srt = whites.sort(1).values
        no_repeat = (srt[:, 1:] != srt[:, :-1]).all(1)
        red_range = red < 26
        return {
            "valid": white_range & no_repeat & red_range,
            "white_out_of_range": ~white_range,
            "white_repeated": white_range & ~no_repeat,
            "red_out_of_range": ~red_range,
        }

    def show(self, picks_row, sort):
        itos = self.meta["itos"]
        toks = [itos[int(t)].replace("\n", "\\n") for t in picks_row]
        if self.game == "pick3":
            return " ".join(toks)
        whites = toks[:5]
        if sort:
            whites = [str(w) for w in sorted(int(w) for w in whites)]
        return " ".join(whites) + " | " + toks[5]

    # --- the played ticket --------------------------------------------------
    def pick(self, tape, seed):
        """First valid attempt from seed, seed + 1, ... -> (picks row, rejects)."""
        ctx = self.context(tape)[None]
        rejects = []
        for n in range(MAX_ATTEMPTS):
            gen = torch.Generator().manual_seed(seed + n)
            picks = self.sample_raw(ctx, gen)
            verdict = self.judge(picks)
            if verdict["valid"][0]:
                return picks[0], rejects
            why = [k for k, v in verdict.items() if k != "valid" and v[0]]
            rejects.append({"seed": seed + n, "attempt": self.show(picks[0], sort=False), "why": why})
        raise RuntimeError(f"no valid ticket in {MAX_ATTEMPTS} attempts from seed {seed}")

    def ticket_row(self, picks_row):
        """A valid pick -> a token row that can join the tape (whites sorted)."""
        if self.game == "pick3":
            return torch.tensor(encode_draw("pick3", "".join(str(int(t)) for t in picks_row)))
        whites = sorted(int(t) + 1 for t in picks_row[:5])
        return torch.tensor(encode_draw("powerball", (whites, int(picks_row[5]) + 1)))


def cmd_pick(args):
    p = Picker(args.ckpt)
    tape = p.frozen_tape()
    if p.history:
        print(f"tape: the {p.history} draws up to {p.meta['dates']['last']} (frozen at the end of the corpus)")
        for row in tape:
            print("  " + p.show(row[:3] if p.game == "pick3" else torch.cat([row[:5], row[6:7]]), sort=True))
    else:
        print("no tape: this is the no-history control")
    for j in range(args.draws):
        seed = args.seed + j * SEED_STRIDE
        picks, rejects = p.pick(tape, seed)
        for r in rejects:
            print(f"  reject  seed {r['seed']}: {r['attempt']}   ({', '.join(r['why'])})")
        label = "pick" if j == 0 else f"pick +{j} (rolled forward)"
        print(f"{label}  seed {seed + len(rejects)}: {p.show(picks, sort=True)}")
        if p.history:
            tape = torch.cat([tape[1:], p.ticket_row(picks)[None]])


def wilson(k, n, z=1.96):
    if n == 0:
        return [0.0, 0.0]
    ph = k / n
    d = 1 + z * z / n
    c = ph + z * z / (2 * n)
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return [(c - h) / d, (c + h) / d]


def cmd_rate(args):
    p = Picker(args.ckpt, device=args.device)
    gen = torch.Generator().manual_seed(args.seed)
    # contexts: the history version reads real tapes, cycling through the
    # windows that end just before each held-out test draw
    test = torch.arange(*p.meta["splits"]["test"])
    counts = {}
    examples = []
    all_picks = []
    if p.history:
        tapes = p.draws[test[:, None] + torch.arange(-p.history, 0)[None, :]]
        lead = torch.full((len(test), 1), p.g["newline"], dtype=torch.long)
        contexts = torch.cat([lead, tapes.reshape(len(test), -1)], dim=1)
    else:
        contexts = torch.full((1, 1), p.g["newline"], dtype=torch.long)
    done = 0
    while done < args.n:
        b = min(args.batch, args.n - done)
        which = (done + torch.arange(b)) % len(contexts)
        picks = p.sample_raw_shared(contexts, which, gen)
        verdict = p.judge(picks)
        for k, v in verdict.items():
            counts[k] = counts.get(k, 0) + int(v.sum())
        bad = (~verdict["valid"]).nonzero().flatten()[:5]
        for i in bad:
            if len(examples) < 12:
                why = [k for k, v in verdict.items() if k != "valid" and v[i]]
                examples.append({"attempt": p.show(picks[i], sort=False), "why": why})
        all_picks.append(picks[verdict["valid"]])
        done += b
    valid = counts.pop("valid")
    out = {
        "checkpoint": args.ckpt, "game": p.game, "history": p.history,
        "step": p.ckpt["iter_num"], "samples": args.n, "seed": args.seed, "temperature": 1.0,
        "valid": valid, "valid_rate": valid / args.n, "valid_rate_ci95": wilson(valid, args.n),
        "rejects_by_rule": counts, "reject_examples": examples,
    }

    if p.game == "powerball":
        # memorization: how often a valid sample, sorted, is a past draw
        with open(os.path.join(p.data_dir, "draws.csv"), newline="") as f:
            past = [([int(r[f"w{i}"]) for i in range(1, 6)], int(r["red"])) for r in csv.DictReader(f)]

        def white_key(w):  # sorted whites -> one integer
            return sum(int(x) * 70 ** i for i, x in enumerate(w))
        past_whites = {white_key(w) for w, _ in past}
        past_full = {white_key(w) * 100 + r for w, r in past}
        picks = torch.cat(all_picks)
        whites = picks[:, :5].sort(1).values + 1
        wkey = sum(whites[:, i] * 70 ** i for i in range(5))
        fkey = wkey * 100 + picks[:, 5] + 1
        hit_w = int(torch.isin(wkey, torch.tensor(sorted(past_whites))).sum())
        hit_f = int(torch.isin(fkey, torch.tensor(sorted(past_full))).sum())
        chance_w = len(past_whites) / math.comb(69, 5)
        chance_f = len(past_full) / GAMES["powerball"]["outcomes"]
        out["memorization"] = {
            "past_draws": len(past),
            "valid_samples": valid,
            "full_ticket": {"matches": hit_f, "rate": hit_f / valid, "chance_rate": chance_f,
                            "expected_by_chance": chance_f * valid},
            "five_whites": {"matches": hit_w, "rate": hit_w / valid, "chance_rate": chance_w,
                            "expected_by_chance": chance_w * valid},
        }
    if args.out:
        with open(args.out, "w") as f:
            json.dump(out, f, indent=1)
            f.write("\n")
    print(json.dumps({k: v for k, v in out.items() if k != "reject_examples"}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("pick", help="print one ticket (or a rolled-forward run of them)")
    a.add_argument("--ckpt", default=HERE, help="run dir or a .pt path (default: this folder)")
    a.add_argument("--seed", type=int, default=0)
    a.add_argument("--draws", type=int, default=1, help="roll forward this many draws")
    a.set_defaults(fn=cmd_pick)
    b = sub.add_parser("rate", help="raw valid-ticket rate and the memorization check")
    b.add_argument("--ckpt", default=HERE)
    b.add_argument("--n", type=int, default=100000)
    b.add_argument("--seed", type=int, default=0)
    b.add_argument("--batch", type=int, default=500,
                   help="samples per chunk; the attention cache is ~0.3 MB per sample, so keep this small")
    b.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    b.add_argument("--out")
    b.set_defaults(fn=cmd_rate)
    args = ap.parse_args()
    assert K_HISTORY == 8
    args.fn(args)


if __name__ == "__main__":
    main()
