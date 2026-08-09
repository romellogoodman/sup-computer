"""pona_tok.py -- the word-level tokenizer contract for the word arm.

One token = one Toki Pona word (or one punctuation mark, or newline). The
vocabulary IS the keyboard: ~130 lexicon words + punctuation + the corpus's
frequent proper names, with two fallbacks (<unk> for out-of-list lowercase
words, <name> for out-of-list capitalized names).

Used by data/prepare.py (encoding) and harness.py / the chat UI (decoding --
core sample.py's raw join doesn't know about spaces; detok() here does).
"""
from __future__ import annotations

import re
from collections import Counter

UNK = "<unk>"
NAME = "<name>"
WORD_RE = re.compile(r"[A-Za-z]+|[.,!?:;\"'()\-]|\n")
NO_SPACE_BEFORE = set(".,!?:;)\"'")
NO_SPACE_AFTER = set("(\"")


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text)


def build_vocab(text: str, name_top: int = 64, min_word_freq: int = 3):
    """Returns (itos: list[str], stoi: dict, stats: dict)."""
    counts = Counter(tokenize(text))
    words, names, punct = {}, {}, {}
    for tok, n in counts.items():
        if tok == "\n" or not tok[0].isalpha():
            punct[tok] = n
        elif tok[0].isupper():
            names[tok] = n
        else:
            words[tok] = n
    kept_words = sorted(w for w, n in words.items() if n >= min_word_freq)
    kept_names = [w for w, _ in sorted(names.items(), key=lambda kv: -kv[1])[:name_top]]
    itos = [UNK, NAME] + sorted(punct) + kept_words + sorted(kept_names)
    stoi = {t: i for i, t in enumerate(itos)}
    stats = {
        "vocab_size": len(itos),
        "lexicon_words": len(kept_words),
        "names_kept": len(kept_names),
        "punct": len(punct),
        "word_types_dropped": len(words) - len(kept_words),
        "name_types_dropped": len(names) - len(kept_names),
        "unk_token_rate": sum(n for w, n in words.items() if n < min_word_freq)
                          / max(1, sum(counts.values())),
        "name_token_rate": sum(n for w, n in names.items() if w not in set(kept_names))
                           / max(1, sum(counts.values())),
    }
    return itos, stoi, stats


def encode(text: str, stoi: dict) -> list[int]:
    ids = []
    for tok in tokenize(text):
        if tok in stoi:
            ids.append(stoi[tok])
        elif tok[0].isupper():
            ids.append(stoi[NAME])
        else:
            ids.append(stoi[UNK])
    return ids


def detok(tokens: list[str]) -> str:
    """Inverse of tokenize up to whitespace: rebuild readable text."""
    out = []
    for tok in tokens:
        if tok == "\n":
            if out and out[-1] == " ":
                out.pop()
            out.append("\n")
            continue
        if out and out[-1] not in ("\n",) and tok not in NO_SPACE_BEFORE \
                and (not out or out[-1] not in NO_SPACE_AFTER):
            if out[-1] != " ":
                out.append(" ")
        out.append(tok)
    return "".join(out).strip()
