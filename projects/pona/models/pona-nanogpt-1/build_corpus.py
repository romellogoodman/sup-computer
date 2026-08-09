"""build_corpus.py -- clean, filter, dedup, and gate the natural corpus.

Inputs (from the fetch_* scripts): raw/wikipedia.txt, raw/poki.txt,
raw/tatoeba.txt -- one paragraph (or sentence) per line, source-tagged here.

The pipeline, per line:
  1. normalize (NFC, straight quotes, dash/ellipsis cleanup, whitespace)
  2. split into sentences; reject any sentence containing digits, URLs, or
     characters outside the Toki Pona charset (letters + .,!?:;"'()- );
     digits are a deliberate exclusion -- Toki Pona numbers are words
  3. keep sentences sonatoki accepts as Toki Pona (community-standard filter)
  4. reassemble the paragraph from kept sentences
Then across lines:
  5. exact dedup (case-insensitive)
  6. name-blind shape dedup -- capitalized names replaced with a placeholder
     before hashing, which collapses templated Wikipedia stubs
     ("X li ma tomo lon ma Y ...") to one representative each
  7. shuffle (seed 1337) so the 90/10 train/val split sees the same mixture
  8. gate: >= 500,000 chars post-dedup or the project stops here

Writes: data/corpus/natural.txt, research/corpus_stats.json (committed).

Run from the repo root:
    uv run python projects/pona/data/build_corpus.py
"""
import json
import os
import random
import re
import unicodedata

from sonatoki.Configs import PrefConfig
from sonatoki.ilo import Ilo

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT_DIR = os.path.join(HERE, "corpus")
STATS_PATH = os.path.join(HERE, "..", "research", "corpus_stats.json")
GATE_CHARS = 500_000

SOURCES = ["wikipedia", "poki", "tatoeba"]
ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ .,!?:;\"'()-")
URL_RE = re.compile(r"https?://|www\.|@\S+\.")
SENT_SPLIT = re.compile(r"(?<=[.!?])[\"')]*\s+")
NAME_RE = re.compile(r"\b[A-Z][a-z]+\b")

REPLACEMENTS = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "«": '"', "»": '"', "–": "-", "—": "-",
    "…": "...", " ": " ", "​": "", "﻿": "",
}


def normalize(line: str) -> str:
    line = unicodedata.normalize("NFC", line)
    for a, b in REPLACEMENTS.items():
        line = line.replace(a, b)
    line = re.sub(r"^[-\s]+", "", line)          # dialogue dashes / stray indent
    line = re.sub(r"\s+", " ", line).strip()
    return line


def sentence_ok(s: str, counts: dict) -> bool:
    if any(c.isdigit() for c in s):
        counts["digits"] += 1
        return False
    if URL_RE.search(s):
        counts["url"] += 1
        return False
    if any(c not in ALLOWED for c in s):
        counts["charset"] += 1
        return False
    return True


def main():
    ilo = Ilo(**PrefConfig)
    os.makedirs(OUT_DIR, exist_ok=True)

    stats = {s: {"lines_in": 0, "chars_in": 0, "digits": 0, "url": 0, "charset": 0,
                 "not_toki_pona": 0, "sentences_kept": 0, "lines_kept": 0, "chars_kept": 0}
             for s in SOURCES}
    kept_lines = []  # (source, text)

    for source in SOURCES:
        c = stats[source]
        with open(os.path.join(RAW, f"{source}.txt"), encoding="utf-8") as f:
            for raw_line in f:
                line = normalize(raw_line)
                if not line:
                    continue
                c["lines_in"] += 1
                c["chars_in"] += len(line)
                kept_sentences = []
                for s in SENT_SPLIT.split(line):
                    s = s.strip()
                    if len(s) < 3 or not sentence_ok(s, c):
                        continue
                    if ilo.is_toki_pona(s):
                        kept_sentences.append(s)
                    else:
                        c["not_toki_pona"] += 1
                if kept_sentences:
                    text = " ".join(kept_sentences)
                    if len(text) >= 8:
                        kept_lines.append((source, text))
                        c["sentences_kept"] += len(kept_sentences)
                        c["lines_kept"] += 1
                        c["chars_kept"] += len(text)

    # -- dedup --
    exact_seen, shape_seen = set(), set()
    exact_dropped = shape_dropped = 0
    deduped = []
    for source, text in kept_lines:
        exact_key = text.lower()
        if exact_key in exact_seen:
            exact_dropped += 1
            continue
        exact_seen.add(exact_key)
        shape_key = NAME_RE.sub("§", text).lower()
        if shape_key in shape_seen:
            shape_dropped += 1
            continue
        shape_seen.add(shape_key)
        deduped.append((source, text))

    random.Random(1337).shuffle(deduped)
    corpus_text = "\n".join(text for _, text in deduped) + "\n"
    with open(os.path.join(OUT_DIR, "natural.txt"), "w", encoding="utf-8") as f:
        f.write(corpus_text)
    # parallel sidecar: source of each line, for per-source baseline scoring
    with open(os.path.join(OUT_DIR, "natural.sources.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(src for src, _ in deduped) + "\n")

    total_chars = len(corpus_text)
    summary = {
        "sources": stats,
        "dedup": {"exact_dropped": exact_dropped, "shape_dropped": shape_dropped,
                  "lines_after": len(deduped)},
        "per_source_lines_after_dedup": {
            s: sum(1 for src, _ in deduped if src == s) for s in SOURCES},
        "total_chars": total_chars,
        "gate_chars": GATE_CHARS,
        "gate": "CLEAR" if total_chars >= GATE_CHARS else "FAIL",
        "excluded_on_principle": {
            "ma-pona-discord-scrape": "6.39M tokens excluded: not published as a corpus by "
                                      "its community (consent), and live register drift would "
                                      "corrupt the grammaticality metric (see README)."},
    }
    os.makedirs(os.path.dirname(STATS_PATH), exist_ok=True)
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    for s in SOURCES:
        c = stats[s]
        print(f"{s:10s} in {c['lines_in']:6,} lines / {c['chars_in']:9,} ch   "
              f"kept {c['lines_kept']:6,} / {c['chars_kept']:9,} ch   "
              f"(dropped: {c['not_toki_pona']:,} non-TP sent, {c['digits']:,} digit, "
              f"{c['charset']:,} charset, {c['url']:,} url)")
    print(f"dedup: -{exact_dropped:,} exact, -{shape_dropped:,} name-blind shape")
    print(f"corpus: {len(deduped):,} lines, {total_chars:,} chars -> gate {summary['gate']}")


if __name__ == "__main__":
    main()
