"""
linewell -- line-by-line composition through a small language model.

The first instrument is shakespeare-nanogpt-3; any release with a checkpoint
and tokenizer can sit in the well (--model_dir).

The small model is the only source of text: the poem grows one line at a
time, each candidate sampled from the model with the poem-so-far as its
prompt -- next-token prediction at line granularity, through another model.
A pluggable judge accepts or rejects each candidate; accepted lines are
FROZEN. The harness never edits a line and never authors one -- the
no-edits constraint is structural, not behavioral.

Judges:
  band   -- accept when the model's own mean NLL/token for the candidate
            (given the poem so far) falls inside [--band_lo, --band_hi]:
            surprising but not garbled. Free, objective, no LLM needed.
            Defaults calibrated on held-out verse (~p10-p90 of real lines);
            register-blind -- fluent editorial/front-matter prose scores in
            the same band as verse, so drift there needs a different judge.
  llm    -- an instruction-following LLM (via tools/steer, e.g. LM Studio)
            reads the poem and candidate and decides. Taste as orchestration.
  human  -- you, at the terminal. The instrument, played by hand.

Every candidate (kept or not) is logged with its settings, NLL, and the
judge's verdict -- the provenance a report gets written from.

Run from the repo root (the HF `tokenizers` lib reads the frozen release's
committed tokenizer.json):

    uv run --with tokenizers python tools/linewell/compose.py \
        --judge band --lines 8 --start "  ROMEO:"
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import torch
import torch.nn.functional as F

from nanogpt_core.model import GPT, GPTConfig

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))  # tools/ -- for the shared steer layer

DEFAULT_MODEL_DIR = os.path.join(HERE, "..", "..", "projects", "shakespeare", "models", "shakespeare-nanogpt-3")
MAX_LINE_CHARS = 90
NEWLINE = "\n"


class LineWell:
    """The source: a frozen shakespeare release, sampled one line at a time,
    plus the same model's likelihoods for judging what it drew up."""

    def __init__(self, model_dir: str = DEFAULT_MODEL_DIR, device: str = "mps"):
        from tokenizers import Tokenizer

        checkpoint = torch.load(os.path.join(model_dir, "ckpt.pt"), map_location=device, weights_only=True)
        conf = GPTConfig(**checkpoint["model_args"])
        state = checkpoint["model"]
        for k in list(state):
            if k.startswith("_orig_mod."):
                state[k[len("_orig_mod."):]] = state.pop(k)
        self.model = GPT(conf)
        self.model.load_state_dict(state)
        self.model.eval()
        self.model.to(device)
        self.device = device
        self.block_size = conf.block_size
        self.tok = Tokenizer.from_file(os.path.join(model_dir, "shakespeare_xl_bpe1k", "tokenizer.json"))

    def _ids(self, text: str) -> list:
        return self.tok.encode(text).ids

    @torch.no_grad()
    def sample_line(self, context: str, temperature: float = 0.9, topk: int = 40) -> str:
        """Sample text until a newline lands (or the char cap): one candidate
        line, conditioned on the poem so far."""
        ids = self._ids(context)[-self.block_size:]
        idx = torch.tensor([ids], dtype=torch.long, device=self.device)
        out = ""
        while len(out) < MAX_LINE_CHARS:
            logits, _ = self.model(idx[:, -self.block_size:])
            logits = logits[:, -1, :] / max(temperature, 1e-5)
            if topk:
                v, _ = torch.topk(logits, min(topk, logits.size(-1)))
                logits[logits < v[:, [-1]]] = -float("inf")
            nxt = torch.multinomial(F.softmax(logits, dim=-1), num_samples=1)
            idx = torch.cat((idx, nxt), dim=1)
            piece = self.tok.decode([nxt.item()])
            if NEWLINE in piece:
                head, _, tail = piece.partition(NEWLINE)
                out += head
                if out.strip():
                    break
                out = tail  # blank line -- keep drawing until real text lands
            else:
                out += piece
        return out.rstrip()

    @torch.no_grad()
    def line_nll(self, context: str, line: str) -> float:
        """Mean NLL/token (nats) of `line` given `context` -- the model's own
        belief about how inevitably this line follows the poem."""
        ctx_ids = self._ids(context)[-(self.block_size - 32):]
        line_ids = self._ids(line + NEWLINE)
        ids = (ctx_ids + line_ids)[-self.block_size:]
        idx = torch.tensor([ids], dtype=torch.long, device=self.device)
        # Passing targets makes the core model emit logits for EVERY position
        # (inference-mode forward keeps only the last); the loss is ignored.
        logits, _ = self.model(idx, targets=idx)
        logp = F.log_softmax(logits[0, :-1, :], dim=-1)
        n = len(line_ids)
        targets = torch.tensor(ids[1:], device=self.device)
        token_logp = logp[torch.arange(len(targets)), targets]
        return -token_logp[-n:].mean().item()


# --- judges: (poem_so_far: list, candidate: str, nll: float) -> (bool, note) ---

class BandJudge:
    def __init__(self, lo: float, hi: float):
        self.lo, self.hi = lo, hi

    def __call__(self, poem: list, candidate: str, nll: float):
        ok = self.lo <= nll <= self.hi
        return ok, f"nll {nll:.2f} {'in' if ok else 'outside'} [{self.lo}, {self.hi}]"


class HumanJudge:
    def __call__(self, poem: list, candidate: str, nll: float):
        answer = input(f'  keep "{candidate}"  (nll {nll:.2f})  [y/N] ').strip().lower()
        return answer == "y", "human"


LLM_JUDGE_SEED = """You are the editor of a poem being composed one line at a time. \
The lines are sampled from a tiny Shakespeare language model; they cannot be edited, \
only accepted (frozen into the poem forever) or rejected (resampled). Judge the \
candidate ONLY as the next line of this poem: sound, momentum, coherence of image. \
Reject garbled text. Prefer lines that earn their place.

Respond with ONLY a JSON object: {"accept": true or false}"""


class LLMJudge:
    def __init__(self, model_id: str):
        from steer import OpenAICompatClient, Orchestrator

        self.orchestrator = Orchestrator(
            OpenAICompatClient(model_id), LLM_JUDGE_SEED,
            validate=lambda obj: {"accept": bool(obj["accept"])} if isinstance(obj, dict) and "accept" in obj else None,
            fallback={"accept": False},
        )

    def __call__(self, poem: list, candidate: str, nll: float):
        state = "The poem so far:\n" + ("\n".join(poem) if poem else "(empty)") + \
                f'\n\nCandidate next line:\n{candidate}\n\nAccept?'
        return self.orchestrator.decide(state)["accept"], "llm"


def compose(well: LineWell, judge, start: str, lines: int, budget: int,
            temperature: float, topk: int) -> dict:
    poem = [line for line in start.split(NEWLINE) if line] if start else []
    candidates = []
    spent = 0
    while len(poem) < lines and (budget == 0 or spent < budget):
        context = (NEWLINE.join(poem) + NEWLINE) if poem else NEWLINE
        candidate = well.sample_line(context, temperature=temperature, topk=topk)
        spent += 1
        if not candidate.strip():
            candidates.append({"line": candidate, "nll": None, "accepted": False, "note": "empty"})
            continue
        nll = well.line_nll(context, candidate)
        accepted, note = judge(poem, candidate, nll)
        candidates.append({"line": candidate, "nll": round(nll, 3), "accepted": accepted, "note": note})
        print(f'  {"KEEP" if accepted else "pass"}  (nll {nll:.2f})  {candidate}')
        if accepted:
            poem.append(candidate)
    return {
        "poem": poem,
        "start": start,
        "finished": len(poem) >= lines,
        "queries_spent": spent,
        "settings": {"temperature": temperature, "topk": topk},
        "candidates": candidates,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", choices=["band", "llm", "human"], default="band")
    ap.add_argument("--lines", type=int, default=8)
    ap.add_argument("--budget", type=int, default=0, help="max queries; 0 = unlimited")
    ap.add_argument("--start", default="", help="seed line(s); frozen like everything else")
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--topk", type=int, default=40)
    ap.add_argument("--band_lo", type=float, default=2.3)
    ap.add_argument("--band_hi", type=float, default=3.5)
    ap.add_argument("--llm_model", default="olmo-3-7b-instruct")
    ap.add_argument("--model_dir", default=DEFAULT_MODEL_DIR)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--out", default=None, help="write the full provenance JSON here")
    args = ap.parse_args()

    well = LineWell(args.model_dir, device=args.device)
    judge = {"band": lambda: BandJudge(args.band_lo, args.band_hi),
             "llm": lambda: LLMJudge(args.llm_model),
             "human": HumanJudge}[args.judge]()

    result = compose(well, judge, args.start, args.lines, args.budget, args.temperature, args.topk)

    print(f"\n--- poem ({result['queries_spent']} queries) ---\n")
    print(NEWLINE.join(result["poem"]))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nprovenance -> {args.out}")


if __name__ == "__main__":
    main()
