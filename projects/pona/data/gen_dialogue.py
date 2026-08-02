"""gen_dialogue.py -- oracle-filtered synthetic dialogues via tools/synthgen.

The chat round needs turn-taking text no natural source provides (the Discord
scrape stays excluded on principle). The studio's synthgen engine (ADR-0014)
drives every loaded LM Studio model across everyday topics; every generated
sentence then faces the same telo misikeke check the model itself will be
scored by, and a dialogue survives only if ALL of its sentences pass with zero
`error`-category issues. Local models producing confident fake Toki Pona was
the brief's reason to ban synthetic corpora -- the oracle filter is what makes
this round sound: nothing enters the corpus that the arbiter wouldn't accept.

Format (the chat contract, also used by the UI):
    - toki! sina pilin seme?
    - mi pilin pona. sina la seme?
  one dialogue per block, turns prefixed "- ", blank line between dialogues.

Per-model keep rates land in data/dialogue_manifest.json -- "which local model
can actually speak Toki Pona" is a result, not a footnote.

Run from the repo root (LM Studio server up):
    uv run python projects/pona/data/gen_dialogue.py --per-topic 2
    uv run python projects/pona/data/gen_dialogue.py --pilot   # 2 models x 3 topics
"""
import argparse
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "synthgen"))
sys.path.insert(0, os.path.join(HERE, "..", "oracle"))
import synthgen as sg  # noqa: E402
from oracle import check_sentences  # noqa: E402

OUT_TXT = os.path.join(HERE, "corpus", "dialogue.txt")
MANIFEST = os.path.join(HERE, "dialogue_manifest.json")

ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ .,!?:;\"'()-")
SENT_SPLIT = re.compile(r"(?<=[.!?])[\"')]*\s+")

TOPICS = [
    "greeting a friend and asking how they feel",
    "food -- what you want to eat and why",
    "the weather today and how it changes your plans",
    "feelings -- one speaker is sad, the other comforts them",
    "family -- parents, siblings, children",
    "a pet or animal one speaker loves",
    "your home and what is inside it",
    "work -- what you did today and whether it was hard",
    "being tired and wanting to sleep",
    "music -- singing, listening, an instrument",
    "colors of things around you",
    "a trip -- going to another place, by foot or vehicle",
    "water -- rain, a lake, drinking, swimming",
    "playing a game together",
    "learning toki pona and finding it easy or hard",
    "plants and a garden",
    "the body -- head, hands, eyes, being healthy",
    "clothes and what you are wearing",
    "morning and night, sun and moon",
    "being afraid of something small and silly",
    "love and friendship",
    "asking for help moving something heavy",
    "saying goodbye and planning to meet again",
    "asking someone's name and introducing yourself",
]

PROMPT = """Write one short dialogue in Toki Pona (the minimalist constructed language, ~130 words).

Rules:
- 4 to 8 turns, two speakers alternating.
- Every line starts with "- " (dash, space).
- Only common Toki Pona words (nimi pu). No English words, no digits, no numbers.
- Short sentences, 3-8 words each. End every sentence with "." or "!" or "?".
- All lowercase (Toki Pona does not capitalize sentence starts).
- Topic: {topic}

Output only the dialogue lines, nothing else."""


def clean_turn(line: str):
    line = unicodedata.normalize("NFC", line)
    for a, b in {"‘": "'", "’": "'", "“": '"', "”": '"', "«": '"', "»": '"',
                 "–": "-", "—": "-", "…": "..."}.items():
        line = line.replace(a, b)
    line = re.sub(r"\s+", " ", line).strip()
    if not line.startswith("- "):
        return None
    turn = line[2:].strip()
    if not turn or any(c.isdigit() for c in turn) or any(c not in ALLOWED for c in turn):
        return None
    # models love capitalizing sentence starts; toki pona doesn't
    parts = SENT_SPLIT.split(turn)
    fixed = []
    for p in parts:
        p = p.strip()
        if p and p[0].isupper() and (len(p) == 1 or not p[1:2].isupper()):
            p = p[0].lower() + p[1:]  # sentence-initial capital isn't toki pona
        fixed.append(p)
    turn = " ".join(fixed)
    if not re.search(r"[.!?][\"')]*$", turn):
        turn += "."
    return turn


def parse_dialogue(text: str):
    turns = []
    for raw in text.split("\n"):
        t = clean_turn(raw)
        if t:
            turns.append(t)
    return turns if len(turns) >= 3 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=None, help="comma-separated (default: discover)")
    ap.add_argument("--per-topic", type=int, default=2, dest="per_topic")
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--pilot", action="store_true", help="2 models x 3 topics x 1")
    args = ap.parse_args()

    models = ([m.strip() for m in args.models.split(",")] if args.models
              else sg.discover())
    topics = TOPICS
    per_topic = args.per_topic
    if args.pilot:
        models, topics, per_topic = models[:2], topics[:3], 1
    print(f"models: {models}")
    print(f"{len(topics)} topics x {per_topic} per topic")

    stats = {m: {"calls": 0, "empty": 0, "unparseable": 0, "dialogues": 0,
                 "kept": 0, "sentences_failed": 0} for m in models}
    kept_blocks, provenance = [], []
    for model in models:
        for topic in topics:
            prompt = PROMPT.format(topic=topic)
            try:
                samples = sg.generate(model, prompt, n=per_topic,
                                      temperature=args.temperature, max_tokens=420)
            except sg.SynthGenError as e:
                print(f"  !! {model}: {e}")
                continue
            for sample in samples:
                stats[model]["calls"] += 1
                if not sample.text:
                    stats[model]["empty"] += 1
                    continue
                turns = parse_dialogue(sample.text)
                if not turns:
                    stats[model]["unparseable"] += 1
                    continue
                stats[model]["dialogues"] += 1
                sentences = [s.strip() for t in turns for s in SENT_SPLIT.split(t) if s.strip()]
                results = check_sentences(sentences)
                n_bad = sum(1 for r in results
                            if any(e["category"] == "error" for e in r["errors"]))
                if n_bad == 0:
                    stats[model]["kept"] += 1
                    kept_blocks.append("\n".join(f"- {t}" for t in turns))
                    p = sample.provenance()
                    p["topic"] = topic
                    provenance.append(p)
                else:
                    stats[model]["sentences_failed"] += n_bad
        s = stats[model]
        print(f"  {model}: {s['kept']}/{s['calls']} kept "
              f"({s['empty']} empty, {s['unparseable']} unparseable, "
              f"{s['sentences_failed']} failed sentences)")

    # dedup near-identical dialogues (models repeat stock greetings)
    seen, unique = set(), []
    for block, p in zip(kept_blocks, provenance):
        key = re.sub(r"[^a-z ]", "", block.lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append((block, p))

    os.makedirs(os.path.dirname(OUT_TXT), exist_ok=True)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n\n".join(b for b, _ in unique) + "\n")
    manifest = {
        "engine": "tools/synthgen (ADR-0014)",
        "filter": "telo misikeke error-category zero-tolerance per sentence "
                  "+ charset/digit checks + >=3 turns",
        "temperature": args.temperature,
        "per_model": stats,
        "dialogues_kept": len(unique),
        "dedup_dropped": len(kept_blocks) - len(unique),
        "provenance": [p for _, p in unique],
    }
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    total_turns = sum(b.count("\n- ") + 1 for b, _ in unique)
    print(f"kept {len(unique)} dialogues ({total_turns} turns) -> {OUT_TXT}")
    print(f"manifest -> {MANIFEST}")


if __name__ == "__main__":
    main()
