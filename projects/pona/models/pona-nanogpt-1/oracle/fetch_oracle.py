"""fetch_oracle.py -- vendor the grammar oracle.

Clones telo misikeke (MIT, Nicolas Hurtubise) at a pinned commit into
oracle/vendor/ and fetches the Linku word list its rules are built from.
The pin matters: the oracle is the arbiter for every grammaticality number
this project reports, so which snapshot of it ran is part of the result.

Run from the repo root:
    uv run python projects/pona/oracle/fetch_oracle.py
"""
import json
import os
import subprocess
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "vendor")
REPO_URL = "https://gitlab.com/telo-misikeke/telo-misikeke.gitlab.io.git"
REPO_DIR = os.path.join(VENDOR, "telo-misikeke")
PINNED_COMMIT = "0a1852d69cc8034ab925738de08d7032df46474a"  # main, 2026-08-02
LINKU_URL = "https://api.linku.la/v1/words"
LINKU_PATH = os.path.join(VENDOR, "linku.json")
PIN_RECORD = os.path.join(HERE, "oracle_pin.json")


def main():
    os.makedirs(VENDOR, exist_ok=True)
    if not os.path.exists(REPO_DIR):
        print(f"cloning {REPO_URL} ...")
        subprocess.run(["git", "clone", "-q", REPO_URL, REPO_DIR], check=True)
    subprocess.run(["git", "-C", REPO_DIR, "checkout", "-q", PINNED_COMMIT], check=True)

    if not os.path.exists(LINKU_PATH):
        print(f"fetching {LINKU_URL} ...")
        req = urllib.request.Request(
            LINKU_URL, headers={"User-Agent": "sup-computer pona corpus build (research)"})
        with urllib.request.urlopen(req, timeout=30) as res:
            words = json.load(res)
        with open(LINKU_PATH, "w", encoding="utf-8") as f:
            json.dump(words, f, ensure_ascii=False)
    with open(LINKU_PATH, encoding="utf-8") as f:
        words = json.load(f)

    cats = {}
    for w in words.values():
        cats[w.get("usage_category")] = cats.get(w.get("usage_category"), 0) + 1
    record = {
        "oracle": "telo misikeke",
        "repo": REPO_URL,
        "commit": PINNED_COMMIT,
        "license": "MIT",
        "word_list": LINKU_URL,
        "word_count": len(words),
        "usage_categories": cats,
    }
    with open(PIN_RECORD, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print(f"oracle pinned at {PINNED_COMMIT[:12]}; {len(words)} Linku words {cats}")


if __name__ == "__main__":
    main()
