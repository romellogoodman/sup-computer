"""
prepare.py — build the v3 dataset in place (FROZEN release copy).

Self-contained snapshot of the r6 XL data pipeline. It rebuilds, into THIS
folder, the exact train/val bins the vendored engine trains on:

    shakespeare_xl_bpe1k/train.bin   uint16 token ids (enlarged corpus, train)
    shakespeare_xl_bpe1k/val.bin     uint16 token ids (Shakespeare val slice)
    shakespeare_xl_bpe1k/meta.pkl    {"vocab_size": 1024, "tokenizer": "tokenizer.json"}

Two invariants make this reproducible and comparable to the whole series:

  1. The tokenizer is NOT retrained. It is loaded from the COMMITTED
     shakespeare_xl_bpe1k/tokenizer.json (a 1024-token byte-level BPE trained on
     the r6 training corpus). This pins the exact vocabulary; prepare only
     re-encodes with it. tokenizer.json is a small text artifact and is
     committed; the *.bin/*.pkl it produces are gitignored and rebuilt here.

  2. The held-out test slice is EXCLUDED and never duplicated. It is the shared
     projects/shakespeare/test.txt (two levels up); this script reads it only to
     assert the excluded slice still matches, byte-for-byte.

Corpus = the Complete Works of Shakespeare (Gutenberg #100) enlarged with
public-domain early-modern drama (Marlowe, Jonson, Kyd, Webster, Dekker). Same
download + cleaning + splitting as the r6 research round (projects/shakespeare/
data/_xl_corpus.py), vendored here so the snapshot has no cross-folder imports.

Requires the Hugging Face `tokenizers` library (provided ad hoc, not in
pyproject) — run it as:

    uv run --with tokenizers python prepare.py

Downloads are cached in ./shakespeare_xl_raw/ (gitignored).
"""
import os
import re
import pickle
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "shakespeare_xl_bpe1k")   # data_root='.', dataset='shakespeare_xl_bpe1k'
RAW_DIR = os.path.join(HERE, "shakespeare_xl_raw")       # cached Gutenberg downloads (gitignored)
TOKENIZER_PATH = os.path.join(DATA_DIR, "tokenizer.json")  # COMMITTED — do not retrain

TEST_LEN = 250_000
VAL_LEN = 150_000

SHAKESPEARE_ID = 100
# Contemporary early-modern drama (public domain, Project Gutenberg ebook ids) —
# the exact set that enlarged the r6 corpus.
CONTEMPORARIES = [
    (779, "Marlowe — Doctor Faustus"),
    (1094, "Marlowe — Tamburlaine the Great, Part 1"),
    (1589, "Marlowe — Tamburlaine the Great, Part 2"),
    (20288, "Marlowe — Edward the Second"),
    (901, "Marlowe — The Jew of Malta"),
    (4039, "Jonson — Volpone; Or, The Fox"),
    (4081, "Jonson — The Alchemist"),
    (3694, "Jonson — Every Man in His Humour"),
    (6043, "Kyd — The Spanish Tragedy"),
    (2232, "Webster — The Duchess of Malfi"),
    (12915, "Webster — The White Devil"),
    (45357, "Dekker — Plays (Mermaid Series: Shoemaker's Holiday, etc.)"),
]


def _download(ebook_id):
    os.makedirs(RAW_DIR, exist_ok=True)
    path = os.path.join(RAW_DIR, f"pg{ebook_id}.txt")
    if not os.path.exists(path):
        url = f"https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt"
        print(f"downloading {url}")
        urllib.request.urlretrieve(url, path)
    return open(path, encoding="utf-8").read()


def _strip_gutenberg(raw):
    """Strip the Gutenberg header/footer, robust to THE/THIS phrasing."""
    m = re.search(r"\*\*\* START OF TH[EI]S? PROJECT GUTENBERG.*?\*\*\*", raw)
    s = raw.find("\n", m.end()) + 1 if m else 0
    m2 = re.search(r"\*\*\* END OF TH[EI]S? PROJECT GUTENBERG", raw)
    e = m2.start() if m2 else len(raw)
    return raw[s:e].replace("\r\n", "\n").replace("\r", "\n").strip("\n")


def shakespeare_body():
    raw = _download(SHAKESPEARE_ID)
    # match data/shakespeare_full exactly (literal "THE", find-based) so the test
    # slice is bit-identical to the committed projects/shakespeare/test.txt
    s = raw.find("*** START OF THE PROJECT GUTENBERG")
    s = raw.find("\n", s) + 1
    e = raw.find("*** END OF THE PROJECT GUTENBERG")
    return raw[s:e].replace("\r\n", "\n").replace("\r", "\n").strip("\n")


def build_splits():
    """Return (train_text, val_text). The test slice is excluded, never rewritten."""
    body = shakespeare_body()
    p = int(len(body) * 0.45)
    test = body[p : p + TEST_LEN]
    s_pool = body[:p] + body[p + TEST_LEN :]
    val = s_pool[-VAL_LEN:]
    s_train = s_pool[:-VAL_LEN]

    extras_parts = []
    for eid, label in CONTEMPORARIES:
        body_i = _strip_gutenberg(_download(eid))
        extras_parts.append(body_i)
        print(f"  {label:<45} {len(body_i):>9,} chars")
    extras = "\n\n\n".join(extras_parts)

    train = s_train + "\n\n\n" + extras

    print(f"\nShakespeare body     : {len(body):,} chars")
    print(f"  held-out test      : {len(test):,} (== test.txt, excluded)")
    print(f"  val (Shakespeare)  : {len(val):,}")
    print(f"  Shakespeare train  : {len(s_train):,}")
    print(f"contemporary extras  : {len(extras):,}")
    print(f"TOTAL train          : {len(train):,} chars")

    # sanity: the excluded slice must match the committed shared test.txt exactly
    tpath = os.path.join(os.path.dirname(os.path.dirname(HERE)), "test.txt")
    if os.path.exists(tpath):
        committed = open(tpath, encoding="utf-8").read()
        assert committed == test, "held-out slice != projects/shakespeare/test.txt — corpus drift!"
        print(f"test.txt match       : True (len {len(committed):,})")
    else:
        print("test.txt match       : (project-root test.txt not found; skipped check)")
    return train, val


def main():
    if not os.path.exists(TOKENIZER_PATH):
        raise SystemExit(
            "tokenizer.json not found in shakespeare_xl_bpe1k/. The frozen release\n"
            "ships the 1024-token tokenizer committed there; restore it from git.\n"
            "It is NOT retrained — this script only re-encodes with it."
        )
    from tokenizers import Tokenizer

    train_text, val_text = build_splits()

    tok = Tokenizer.from_file(TOKENIZER_PATH)
    vocab_size = tok.get_vocab_size()
    print(f"\ntokenizer            : {TOKENIZER_PATH} (vocab {vocab_size}, not retrained)")

    train_ids = tok.encode(train_text).ids
    val_ids = tok.encode(val_text).ids
    assert max(max(train_ids), max(val_ids)) < 65535, "ids exceed uint16"
    print(f"train                : {len(train_text):,} chars -> {len(train_ids):,} tokens "
          f"({len(train_text)/len(train_ids):.2f} chars/token)")
    print(f"val                  : {len(val_text):,} chars -> {len(val_ids):,} tokens")

    os.makedirs(DATA_DIR, exist_ok=True)
    np.array(train_ids, dtype=np.uint16).tofile(os.path.join(DATA_DIR, "train.bin"))
    np.array(val_ids, dtype=np.uint16).tofile(os.path.join(DATA_DIR, "val.bin"))
    with open(os.path.join(DATA_DIR, "meta.pkl"), "wb") as f:
        pickle.dump({"vocab_size": vocab_size, "tokenizer": "tokenizer.json"}, f)
    print(f"\nwrote train.bin / val.bin / meta.pkl -> {DATA_DIR}")


if __name__ == "__main__":
    main()
