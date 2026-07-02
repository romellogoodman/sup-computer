"""
Shared corpus builder for the Shakespeare v3 "XL" research round (r5).

Enlarges the training corpus beyond Shakespeare's Complete Works with
public-domain early-modern drama from Project Gutenberg (Marlowe, Jonson, Kyd,
Webster), while keeping the held-out test set EXACTLY the existing
projects/shakespeare/test.txt (the 250k-char Shakespeare slice every model in
the series is scored on).

This module owns the download + cleaning + splitting so the four r5 dataset
dirs (bpe1k / bpe4k / bpe16k / gpt2 control) share one corpus and differ only in
tokenizer. Each dataset's prepare.py imports build_splits().

Invariants (matched to data/shakespeare_full/prepare.py so the test slice is bit-
identical and never leaks into training):

  body   = cleaned Complete Works (Gutenberg #100), \r\n normalised, stripped
  p      = int(len(body) * 0.45)
  test   = body[p : p+250_000]            # == projects/shakespeare/test.txt (NOT rewritten here)
  s_pool = body[:p] + body[p+250_000:]    # Shakespeare minus test
  val    = s_pool[-150_000:]              # == data/shakespeare_full val (identical Shakespeare val)
  train  = s_pool[:-150_000] + extras     # Shakespeare-train + all contemporary drama

The tokenizers are trained on `train` only (never on val or test).
"""
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "shakespeare_xl_raw")  # cached Gutenberg downloads (gitignored: raw.txt-style)

TEST_LEN = 250_000
VAL_LEN = 150_000

# Complete Works of Shakespeare — the base corpus (same source + cleaning as
# data/shakespeare_full). Reuse the already-cached raw.txt if present.
SHAKESPEARE_ID = 100
SHAKESPEARE_CACHED = os.path.join(HERE, "shakespeare_full", "raw.txt")

# Contemporary early-modern drama (public domain, Project Gutenberg ebook ids).
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
# Note: Gutenberg #77587 ("The chief Elizabethan dramatists") is a 4.8MB anthology
# of these same authors; skipped deliberately to avoid duplicating the individually
# downloaded plays above (and to limit domain drift away from Shakespeare, which is
# what the held-out test measures).


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
    body = raw[s:e].replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    return body


def shakespeare_body():
    if os.path.exists(SHAKESPEARE_CACHED):
        raw = open(SHAKESPEARE_CACHED, encoding="utf-8").read()
    else:
        raw = _download(SHAKESPEARE_ID)
    # match data/shakespeare_full exactly (literal "THE", find-based)
    s = raw.find("*** START OF THE PROJECT GUTENBERG")
    s = raw.find("\n", s) + 1
    e = raw.find("*** END OF THE PROJECT GUTENBERG")
    return raw[s:e].replace("\r\n", "\n").replace("\r", "\n").strip("\n")


def build_splits(verbose=True):
    """Return (train_text, val_text). Test slice is excluded and never rewritten."""
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
        if verbose:
            print(f"  {label:<45} {len(body_i):>9,} chars")
    extras = "\n\n\n".join(extras_parts)

    train = s_train + "\n\n\n" + extras

    if verbose:
        print(f"\nShakespeare body     : {len(body):,} chars")
        print(f"  held-out test      : {len(test):,} (== test.txt, excluded)")
        print(f"  val (Shakespeare)  : {len(val):,}")
        print(f"  Shakespeare train  : {len(s_train):,}")
        print(f"contemporary extras  : {len(extras):,}")
        print(f"TOTAL train          : {len(train):,} chars")
        # sanity: confirm test slice matches the committed test.txt
        tpath = os.path.join(os.path.dirname(HERE), "test.txt")
        if os.path.exists(tpath):
            committed = open(tpath, encoding="utf-8").read()
            print(f"test.txt match       : {committed == test} (len {len(committed):,})")
    return train, val


if __name__ == "__main__":
    build_splits()
