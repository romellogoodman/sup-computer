"""talk.py -- talk with a pona chat checkpoint in the terminal.

The terminal preview of the keyboard UI: your line and the model's reply
alternate as "- " turns, with a rolling context window. Word-arm checkpoints
only (the vocab is the keyboard; decoding goes through pona_tok.detok).

Run from the repo root:
    uv run python projects/pona/talk.py --out_dir projects/pona/runs/chat-r1
    uv run python projects/pona/talk.py --out_dir ... --show-keys   # top next-word suggestions
"""
from __future__ import annotations

import argparse
import os
import sys

import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
import pona_tok  # noqa: E402
from checkpoint import load_model  # vendored: no cross-folder imports in a frozen release  # noqa: E402
from harness import load_meta  # noqa: E402

HISTORY_TURNS = 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--max-tokens", type=int, default=36, dest="max_tokens")
    ap.add_argument("--show-keys", action="store_true", dest="show_keys",
                    help="print the top-5 next-word suggestions before each reply")
    args = ap.parse_args()

    model, checkpoint = load_model(args.out_dir, args.device)
    model.eval()
    meta = load_meta(checkpoint)
    assert meta.get("arm") == "word", "talk.py expects a word-arm checkpoint"
    stoi, itos = meta["stoi"], meta["itos"]
    nl = stoi["\n"]

    print("o toki tawa ilo! (ctrl-d to leave)\n")
    turns: list[str] = []
    while True:
        try:
            user = input("sina: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\ntawa pona!")
            break
        if not user:
            continue
        turns.append(user)
        context = "\n" + "\n".join(f"- {t}" for t in turns[-HISTORY_TURNS:]) + "\n- "
        ids = pona_tok.encode(context, stoi)
        idx = torch.tensor([ids], dtype=torch.long, device=args.device)

        if args.show_keys:
            with torch.no_grad():
                logits, _ = model(idx[:, -model.config.block_size:])
            probs = F.softmax(logits[0, -1], dim=-1)
            top = torch.topk(probs, 5)
            keys = ", ".join(f"{itos[i]} {p:.0%}" for p, i in
                             zip(top.values.tolist(), top.indices.tolist()))
            print(f"  [keys: {keys}]")

        with torch.no_grad():
            out = model.generate(idx, args.max_tokens,
                                 temperature=args.temperature, top_k=None)
        tail = out[0, len(ids):].tolist()
        if nl in tail:
            tail = tail[:tail.index(nl)]
        reply = pona_tok.detok([itos[i] for i in tail]).strip() or "..."
        print(f"ilo:  {reply}")
        turns.append(reply)


if __name__ == "__main__":
    main()
