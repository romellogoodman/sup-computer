"""fetch_deck.py — fetch the published Oblique Strategies card lists for the leakage check.

The deck is Brian Eno and Peter Schmidt's. It is fetched to data/deck/
(gitignored) only so filter.py can prove no generated line reproduces a card;
it is never committed, never shown to a generator and never trained on.

Sources are two public transcriptions: the four editions plus a condensed
list, and one independent list. The union is 258 distinct cards.

Run from the repo root:
    uv run python projects/oblique/data/fetch_deck.py
"""
import hashlib
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DECK_DIR = os.path.join(HERE, "deck")

ZZKT = "https://raw.githubusercontent.com/zzkt/oblique-strategies/endless/strategies/"
SOURCES = {
    "edition-1.txt": ZZKT + "oblique-strategies-edition-1.txt",
    "edition-2.txt": ZZKT + "oblique-strategies-edition-2.txt",
    "edition-3.txt": ZZKT + "oblique-strategies-edition-3.txt",
    "edition-4.txt": ZZKT + "oblique-strategies-edition-4.txt",
    "condensed.txt": ZZKT + "oblique-strategies-condensed.txt",
    "independent.txt": "https://raw.githubusercontent.com/ceejbot/oblique-strategies/master/strategies.txt",
}


def main():
    os.makedirs(DECK_DIR, exist_ok=True)
    for name, url in SOURCES.items():
        with urllib.request.urlopen(url, timeout=30) as r:
            body = r.read()
        with open(os.path.join(DECK_DIR, name), "wb") as f:
            f.write(body)
        print(f"{name}: {len(body.splitlines())} lines, sha256 {hashlib.sha256(body).hexdigest()[:16]}")


if __name__ == "__main__":
    main()
