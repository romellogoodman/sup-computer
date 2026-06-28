"""
The control-line prime — the single source of truth for how a green-light
intensity is encoded into text.

In the working project at the repo root this helper lives in `generate.py`
(which also pulls in the Claude API). The frozen release extracts it here so the
folder has NO `anthropic` / API dependency: `eval_dial.py` imports `build_prime`
from this module and nothing reaches out of the folder.

LOAD-BEARING CONTRACT — this exact string shape is the interface the model was
trained on (the corpus in `raw.txt` is built from it) and is primed with at
sample time. The v3 "louder" format repeats the tag 3x and adds a per-level word
so the dial signal carries real character-mass right above the story body; that
is the change that made the intensity dial actually move (see ../../research/).
"""

LEVEL_WORDS = {1: "faint", 2: "soft", 3: "strong", 4: "heavy", 5: "total"}


def build_prime(topic, level):
    """Return the `[green=N] [green=N] [green=N] obsession=<word>\\ntopic: ...\\n`
    control-line prime for a given topic and intensity level (1..5)."""
    word = LEVEL_WORDS.get(level, "total")
    tag = f"[green={level}]"
    return f"{tag} {tag} {tag} obsession={word}\ntopic: {topic}\n"
