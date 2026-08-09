"""prepare.py -- tokenize the corpus for one arm.

Two arms, two tokenizers, never shared (see CLAUDE.md):

  --arm char   one character = one token (the studio's usual contract);
               vocab is whatever characters the corpus actually contains
  --arm word   one Toki Pona word = one token (pona_tok.py); the vocab IS
               the keyboard the chat UI will render

Both write train.bin / val.bin / meta.pkl (ADR-0012 contract) into
data/tokenized-<arm>/. The word meta.pkl additionally records the arm and
tokenizer name so a checkpoint knows how it must be decoded.

Run from the repo root:
    uv run python projects/pona/data/prepare.py --arm char
    uv run python projects/pona/data/prepare.py --arm word
"""
import argparse
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pona_tok  # noqa: E402

CORPUS = os.path.join(HERE, "corpus", "natural.txt")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["char", "word"])
    ap.add_argument("--corpus", default=CORPUS,
                    help="corpus file (default: data/corpus/natural.txt)")
    ap.add_argument("--out-suffix", default=None,
                    help="tokenized dir suffix (default: the arm name)")
    args = ap.parse_args()

    with open(args.corpus, encoding="utf-8") as f:
        data = f.read()
    print(f"corpus: {len(data):,} chars, {data.count(chr(10)):,} lines")

    out_dir = os.path.join(HERE, f"tokenized-{args.out_suffix or args.arm}")
    os.makedirs(out_dir, exist_ok=True)

    if args.arm == "char":
        chars = sorted(set(data))
        stoi = {ch: i for i, ch in enumerate(chars)}
        itos = {i: ch for i, ch in enumerate(chars)}
        ids = [stoi[c] for c in data]
        meta = {"vocab_size": len(chars), "stoi": stoi, "itos": itos,
                "arm": "char", "tokenizer": "pona-char-v1"}
        print(f"char vocab: {len(chars)} -> {''.join(repr(c)[1:-1] for c in chars)}")
    else:
        itos_list, stoi, stats = pona_tok.build_vocab(data)
        ids = pona_tok.encode(data, stoi)
        itos = {i: t for i, t in enumerate(itos_list)}
        meta = {"vocab_size": len(itos_list), "stoi": stoi, "itos": itos,
                "arm": "word", "tokenizer": "pona-word-v1", "vocab_stats": stats}
        print(f"word vocab: {stats['vocab_size']} "
              f"({stats['lexicon_words']} words + {stats['names_kept']} names + "
              f"{stats['punct']} punct + 2 specials)")
        print(f"  unk rate {stats['unk_token_rate']:.4%}, "
              f"name-fallback rate {stats['name_token_rate']:.4%}")

    n = len(ids)
    train_ids = np.array(ids[: int(n * 0.9)], dtype=np.uint16)
    val_ids = np.array(ids[int(n * 0.9):], dtype=np.uint16)
    train_ids.tofile(os.path.join(out_dir, "train.bin"))
    val_ids.tofile(os.path.join(out_dir, "val.bin"))
    with open(os.path.join(out_dir, "meta.pkl"), "wb") as f:
        pickle.dump(meta, f)
    print(f"train: {len(train_ids):,} tokens   val: {len(val_ids):,} tokens -> {out_dir}")


if __name__ == "__main__":
    main()
