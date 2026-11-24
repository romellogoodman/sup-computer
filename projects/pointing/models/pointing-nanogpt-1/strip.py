"""strip.py -- the pointing transform: a line of text -> its words and its marks.

One function does the whole job. `strip_line` lowercases a line, pulls every
punctuation mark out of it, and returns the two halves:

    words   the letters that are left, one string per word
    gaps    the marks that were removed, as n + 1 lists: gaps[0] sits before
            the first word, gaps[i] between word i and word i + 1, gaps[n]
            after the last word

`encode` then writes the training pair. The model reads the words and emits
ONE slot per gap, each word's slot preceded by the word's first letter (its
anchor), so it never has to count:

    the quick brown fox|_t_q_b_f.
    enter hamlet|[e_h]

The rules, each one a decision recorded in the README:

  * Everything is lowercased. Casing is not in v1.
  * An apostrophe or a hyphen with a letter on BOTH sides is a letter
    (don't, o'er, well-met). Anywhere else an apostrophe is a mark and a
    hyphen is a dash.
  * Quotes and word-edge apostrophes are labelled by the side they attach
    to, because one gap can hold either: `“` and `‘` attach to the word
    after, `”` and `’` to the word before. ('tis -> ‘ before "tis";
    th' -> ’ after "th".) The source glyph is ignored; position decides.
  * A dash is `—`, `–`, two or more hyphens, or any hyphen that is not
    between two letters. An ellipsis is `…` or three or more dots.
  * A gap that held several marks keeps the FIRST in reading order
    (`collapse`); the full list stays in `gaps` so the loss can be counted.
  * Digits are word characters. Accents fold to ASCII. Italic markup
    (`_`, `~`, `^`) is deleted; any other symbol becomes a space.

The other half -- the marks with the letters deleted -- is the "skeleton"
corpus a later round can build from the same `gaps`.
"""
from __future__ import annotations

import re
import unicodedata

SEP = "|"    # between the words and the slot string
NONE = "_"   # an empty slot

# The label alphabet: every mark a slot can hold, in a fixed order.
MARKS = [",", ".", ";", ":", "?", "!", "—", "…", "“", "”", "‘", "’", "(", ")", "[", "]"]
MARK_NAMES = {
    ",": "comma", ".": "period", ";": "semicolon", ":": "colon",
    "?": "question", "!": "exclamation", "—": "dash", "…": "ellipsis",
    "“": "quote-open", "”": "quote-close",
    "‘": "apostrophe-leading", "’": "apostrophe-trailing",
    "(": "paren-open", ")": "paren-close", "[": "bracket-open", "]": "bracket-close",
}
TERMINALS = {".", "?", "!"}

_WORD = "abcdefghijklmnopqrstuvwxyz0123456789"
_DIRECT = set(",.;:?!()[]")
_FOLD = {"æ": "ae", "œ": "oe", "ß": "ss", "ð": "d", "þ": "th", "ø": "o"}
_DELETE = set("_~^")
_ELLIPSIS = re.compile(r"\.(?:\s?\.){2,}")
_DASH = re.compile(r"-{2,}|[—–―‒]")


def _normalise(text: str) -> str:
    text = text.lower()
    text = "".join(_FOLD.get(c, c) for c in text)
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("…", " … ")
    text = _ELLIPSIS.sub(" … ", text)
    text = _DASH.sub(" — ", text)
    return "".join(c for c in text if c not in _DELETE)


def strip_line(text: str):
    """-> (words, gaps). gaps has len(words) + 1 lists of marks, uncollapsed."""
    s = _normalise(text)
    words: list[str] = []
    gaps: list[list[str]] = [[]]
    cur: list[str] = []
    spaced = True  # has whitespace (or the line start) come since the last word?

    def close_word():
        nonlocal cur, spaced
        if cur:
            words.append("".join(cur))
            gaps.append([])
            cur = []
            spaced = False

    n = len(s)
    for i, c in enumerate(s):
        if c in _WORD:
            cur.append(c)
            continue
        if c in "'-" and cur and i + 1 < n and s[i + 1] in _WORD:
            cur.append(c)  # a letter on both sides: orthography, not a mark
            continue
        close_word()
        if c in _DIRECT or c in "—…":
            gaps[-1].append(c)
        elif c == "-":
            gaps[-1].append("—")
        elif c == '"':
            gaps[-1].append("“" if spaced else "”")
        elif c == "'":
            gaps[-1].append("‘" if spaced else "’")
        else:
            spaced = True  # whitespace, and every symbol outside the alphabet
    close_word()
    return words, gaps


def collapse(gaps) -> list[str]:
    """One slot per gap: the first mark in reading order, or NONE."""
    return [g[0] if g else NONE for g in gaps]


def slot_string(words, slots) -> str:
    out = [slots[0]]
    for w, m in zip(words, slots[1:]):
        out.append(w[0])
        out.append(m)
    return "".join(out)


def encode(text: str):
    """-> (input, slot string), or None when the line has no words."""
    words, gaps = strip_line(text)
    if not words:
        return None
    return " ".join(words), slot_string(words, collapse(gaps))


def render(words, slots) -> str:
    """Put a slot string's marks back on the words, for reading."""
    out = []
    for i, w in enumerate(words):
        lead = slots[i] if slots[i] in "“‘([" else ""
        if i == 0 and slots[0] != NONE and not lead:
            lead = slots[0]
        trail = slots[i + 1] if slots[i + 1] != NONE and slots[i + 1] not in "“‘([" else ""
        out.append(lead + w + trail)
    return " ".join(out)


if __name__ == "__main__":
    import sys

    for line in sys.stdin:
        pair = encode(line)
        if pair:
            print(pair[0] + SEP + pair[1])
