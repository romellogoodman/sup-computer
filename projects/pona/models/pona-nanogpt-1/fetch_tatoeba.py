"""fetch_tatoeba.py -- download every Toki Pona sentence on Tatoeba.

Source: https://downloads.tatoeba.org/exports/per_language/tok/ (CC BY 2.0 FR;
Toki Pona's ISO 639-3 code is `tok`). Short, simple, largely conversational
sentence material -- ~78k sentences as of 2026-08.

Writes: data/raw/tatoeba.txt (one sentence per line)

Run from the repo root:
    uv run python projects/pona/data/fetch_tatoeba.py
"""
import bz2
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
URL = "https://downloads.tatoeba.org/exports/per_language/tok/tok_sentences.tsv.bz2"
TSV_PATH = os.path.join(RAW, "tok_sentences.tsv.bz2")
OUT_PATH = os.path.join(RAW, "tatoeba.txt")


def main():
    os.makedirs(RAW, exist_ok=True)
    if not os.path.exists(TSV_PATH):
        print(f"downloading {URL} ...")
        urllib.request.urlretrieve(URL, TSV_PATH)

    sentences = []
    with bz2.open(TSV_PATH, "rt", encoding="utf-8") as f:
        for row in f:
            parts = row.rstrip("\n").split("\t")
            if len(parts) == 3 and parts[1] == "tok":
                s = parts[2].strip()
                if s:
                    sentences.append(s)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(sentences) + "\n")
    print(f"wrote {len(sentences):,} sentences -> {OUT_PATH}")


if __name__ == "__main__":
    main()
