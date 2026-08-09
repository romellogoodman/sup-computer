"""oracle.py -- Python wrapper around the vendored telo misikeke checker.

Usage:
    from oracle import check_sentences, pass_rate
    results = check_sentences(["mi moku e kili.", "mi li moku."])
    # -> [{"errors": []}, {"errors": [{"rule": "noLiAfterMiSina", ...}]}]

Batches through node in chunks; requires oracle/fetch_oracle.py to have run.
"""
from __future__ import annotations

import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "check.cjs")
CHUNK = 1000


def check_sentences(sentences: list[str], node: str = "node") -> list[dict]:
    out: list[dict] = []
    for i in range(0, len(sentences), CHUNK):
        batch = sentences[i:i + CHUNK]
        proc = subprocess.run(
            [node, CHECK],
            input=json.dumps(batch).encode("utf-8"),
            capture_output=True,
            check=True,
        )
        out.extend(json.loads(proc.stdout.decode("utf-8")))
    return out


def passes(result: dict) -> bool:
    return not result["errors"]


def pass_rate(sentences: list[str]) -> float:
    if not sentences:
        return 0.0
    results = check_sentences(sentences)
    return sum(1 for r in results if passes(r)) / len(sentences)
