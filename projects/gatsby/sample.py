"""
Sample from a trained gatsby-nanogpt model — core engine, byte-level BPE.

Gatsby migrated off its vendored char-level engine onto the shared `core` engine
(docs/adr/0023). This driver loads core's GPT and the byte-level BPE tokenizer
(via the meta.pkl seam, ADR-0012). It primes the model with a control line and
lets it continue:

    [green=N] [green=N] [green=N] obsession=<word>
    topic: <a topic>
    <a TinyStories-register story, fixated on a green light at intensity N>

Run from the repo root, with the tokenizers lib provided ad hoc:

    uv run --with tokenizers python projects/gatsby/sample.py \
        --out_dir projects/gatsby/runs/migrate-bpe-r1 \
        --start "[green=5] [green=5] [green=5] obsession=total
topic: a dog and a balloon
" --num_samples 3 --max_new_tokens 200

Pass arbitrary operator text safely via a file with --start "FILE:prompt.txt".
"""
import argparse
import os

import torch

from _runtime import generate, load_model_and_tokenizer, pick_device

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", default=os.path.join(HERE, "runs", "migrate-bpe-r1"))
    ap.add_argument("--data_dir", default=os.path.join(HERE, "data"))
    ap.add_argument("--start", default="[green=5] [green=5] [green=5] obsession=total\ntopic: a lost kitten\n")
    ap.add_argument("--num_samples", type=int, default=5)
    ap.add_argument("--max_new_tokens", type=int, default=200)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top_k", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--device", default=None)
    a = ap.parse_args()

    device = pick_device(a.device)
    model, tok = load_model_and_tokenizer(a.out_dir, a.data_dir, device)

    start = a.start
    if start.startswith("FILE:"):
        with open(start[5:], "r", encoding="utf-8") as f:
            start = f.read()

    for i in range(a.num_samples):
        text = generate(model, tok, start, a.max_new_tokens, device,
                        seed=a.seed + i, temperature=a.temperature, top_k=a.top_k)
        print(text)
        print("---------------")


if __name__ == "__main__":
    main()
