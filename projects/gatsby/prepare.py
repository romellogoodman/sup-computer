"""
Prepare the synthetic Gatsby corpus for the shared core engine — BPE edition.

Gatsby has MIGRATED off its vendored base char-level engine onto the modern
`core` engine (RoPE / RMSNorm / bias-free) with **byte-level BPE** tokenization
(see docs/adr/0023). The old char-level tokenizer conditioned too weakly on the
`[green=N] topic: ...` control line: a char-LM sees the tag and the topic word as
long strings of low-weight characters dozens of positions back. BPE turns them
into a handful of high-weight tokens, which is the named structural fix for
gatsby's unreliable topic-honoring (obsession-on-a-dial §6).

This script trains a small byte-level BPE tokenizer on the corpus and writes the
dataset the shared engine trains on:

    data/gatsby_bpe/train.bin      uint16 token ids (90%)
    data/gatsby_bpe/val.bin        uint16 token ids (10%)
    data/gatsby_bpe/tokenizer.json the trained HF tokenizer (small text artifact,
                                   committed — it is not a weight; ADR-0012 seam)
    data/gatsby_bpe/meta.pkl       {"vocab_size": N, "tokenizer": "tokenizer.json"}

meta.pkl IS the tokenizer contract (ADR-0012): core/nanogpt_core/train.py reads
`vocab_size` from it; the project-local sample.py / eval_dial.py /
generate_samples.py read `tokenizer` and load tokenizer.json (core's own
sample/eval only understand char stoi or GPT-2 BPE, hence the project-local seam
shakespeare's eval_xl.py/sample_xl.py established).

The byte-level initial alphabet (all 256 bytes) makes the tokenizer lossless:
every character in the corpus and in any operator prompt encodes with no UNK.

The corpus (data/raw.txt) is UNCHANGED this round — the whole point of the
migration experiment is to isolate the tokenizer+engine switch as a single
variable against gatsby-nanogpt-2's documented behaviour.

Run from the repo root (`tokenizers` is declared in the project's pyproject):

    uv run python projects/gatsby/prepare.py
"""
import os
import pickle

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw.txt")
OUT_DIR = os.path.join(HERE, "data", "gatsby_bpe")  # data_root=<.../data>, dataset='gatsby_bpe'

# Small on purpose. The corpus is tiny (~1.53M chars); a small byte-level vocab
# keeps every control-line token frequent and well-trained, and sidesteps the
# large-vocab float16 overflow that diverged shakespeare's 16k BPE run on MPS
# (core's GradScaler is CUDA-only). We also train in float32 (see config.py).
VOCAB_SIZE = 1024

if not os.path.exists(RAW):
    raise SystemExit(
        "data/raw.txt not found. It is the committed v2 mixture corpus; if it is\n"
        "missing, regenerate it with generate_mixture.py (see README.md)."
    )


def train_tokenizer(train_text, vocab_size, save_path):
    """Train a lossless byte-level BPE on the TRAINING text only (no val leakage)."""
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

    tok = Tokenizer(models.BPE(unk_token=None))
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        special_tokens=[],
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),  # all 256 bytes -> lossless
        show_progress=False,
    )
    tok.train_from_iterator([train_text], trainer=trainer)
    tok.save(save_path)
    return tok


def main():
    with open(RAW, "r", encoding="utf-8") as f:
        data = f.read()
    print(f"corpus: {len(data):,} characters")

    # 90/10 split, same as the char-level prepare.py it replaces.
    n = len(data)
    train_text = data[: int(n * 0.9)]
    val_text = data[int(n * 0.9):]

    os.makedirs(OUT_DIR, exist_ok=True)
    tok_path = os.path.join(OUT_DIR, "tokenizer.json")
    tok = train_tokenizer(train_text, VOCAB_SIZE, tok_path)
    actual_vocab = tok.get_vocab_size()

    train_ids = tok.encode(train_text).ids
    val_ids = tok.encode(val_text).ids
    assert max(max(train_ids), max(val_ids)) < 65535, "ids exceed uint16"

    np.array(train_ids, dtype=np.uint16).tofile(os.path.join(OUT_DIR, "train.bin"))
    np.array(val_ids, dtype=np.uint16).tofile(os.path.join(OUT_DIR, "val.bin"))
    with open(os.path.join(OUT_DIR, "meta.pkl"), "wb") as f:
        pickle.dump({"vocab_size": actual_vocab, "tokenizer": "tokenizer.json"}, f)

    print(
        f"vocab={actual_vocab}  "
        f"train {len(train_text):,} chars -> {len(train_ids):,} tok "
        f"({len(train_text)/len(train_ids):.2f} chars/tok)  "
        f"val {len(val_text):,} -> {len(val_ids):,} tok"
    )
    print(f"wrote train.bin / val.bin / tokenizer.json / meta.pkl -> {OUT_DIR}")

    # Sanity: show how the load-bearing control line tokenizes (ADR-0023 asks for
    # this to be inspected — the whole hypothesis is that these become compact,
    # consistent tokens instead of long char strings).
    sample_ctrl = "[green=5] [green=5] [green=5] obsession=total\ntopic: a robot who wanted a friend\n"
    enc = tok.encode(sample_ctrl)
    print("\ncontrol-line tokenization check:")
    print(f"  {sample_ctrl!r}")
    print(f"  -> {len(enc.ids)} tokens")
    print(f"  pieces: {enc.tokens}")


if __name__ == "__main__":
    main()
