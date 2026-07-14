"""
Byte-level BPE helpers for the r5 XL round (custom corpus-trained vocabularies).

Trains small byte-level BPE tokenizers on the TRAINING corpus only (never val or
test.txt), using the Hugging Face `tokenizers` library. Run the prepare scripts
with the lib provided ad hoc (not added to pyproject):

    uv run --with tokenizers python projects/shakespeare/data/shakespeare_xl_bpe1k/prepare.py

The initial alphabet is the full 256-byte ByteLevel alphabet, so every dataset is
lossless (no UNK) and test.txt always encodes completely — important because BPC's
denominator is the full character count of the test text.

Dataset contract for these custom-vocab dirs:
  train.bin / val.bin  : uint16 token ids (all vocabs < 65535)
  tokenizer.json       : the trained HF tokenizer (committed; small, not a weight)
  meta.pkl             : {"vocab_size": N, "tokenizer": "tokenizer.json"}
                         -> train.py reads vocab_size; core's eval/sample read
                            "tokenizer" and load tokenizer.json (the ADR-0012
                            meta.pkl seam, absorbed into core by ADR-0029).
"""
import os
import pickle

import numpy as np


def train_tokenizer(train_text, vocab_size, save_path):
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


def load_tokenizer(path):
    from tokenizers import Tokenizer

    return Tokenizer.from_file(path)


def build_bpe_dataset(dirname, vocab_size, train_text, val_text):
    """Train a tokenizer at vocab_size, encode train/val to uint16 bins, write meta."""
    here = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(here, dirname)
    os.makedirs(d, exist_ok=True)
    tok_path = os.path.join(d, "tokenizer.json")

    tok = train_tokenizer(train_text, vocab_size, tok_path)
    actual_vocab = tok.get_vocab_size()

    train_ids = tok.encode(train_text).ids
    val_ids = tok.encode(val_text).ids
    assert max(max(train_ids), max(val_ids)) < 65535, "ids exceed uint16"

    np.array(train_ids, dtype=np.uint16).tofile(os.path.join(d, "train.bin"))
    np.array(val_ids, dtype=np.uint16).tofile(os.path.join(d, "val.bin"))
    with open(os.path.join(d, "meta.pkl"), "wb") as f:
        pickle.dump({"vocab_size": actual_vocab, "tokenizer": "tokenizer.json"}, f)

    print(
        f"data/{dirname}/  vocab={actual_vocab}  "
        f"train {len(train_text):,} chars -> {len(train_ids):,} tok "
        f"({len(train_text)/len(train_ids):.2f} chars/tok)  "
        f"val {len(val_text):,} -> {len(val_ids):,} tok"
    )
    return actual_vocab, len(train_ids), len(val_ids)
