"""
Generate the Gatsby corpus from a MIXTURE of local LLMs (via LM Studio), instead
of the Claude API (`generate.py`). Same task, same `[green=N]` contract — only
the writers change: several open models each contribute a share of the topics,
so the corpus carries diverse "voices" and costs $0 to make.

The engine lives one tool away (`tools/synthgen/`): this file is the gatsby-
specific driver (prompts, the green-light dial, the blend, corpus cleaning).
Per the studio convention, it's committed alongside the corpus it produced.

Blend (by topic — each topic's five levels are written by ONE model, so the
within-topic dial stays a clean contrastive signal; models rotate across topics):

    granite-4.1-8b ............ 40%   backbone: fastest, cleanest, best topic-honoring
    google/gemma-4-26b ........ 30%   best dial modulation + most TinyStories-authentic
    olmo-3-7b-instruct ........ 15%   AllenAI voice (distinct corpus); cleaned
    ministral-3-8b-instruct ... 15%   richest prose diversity; cleaned

(qwen3.6 was dropped: ~5-10x slower per story and runs long — see research/log.)

Stories are cleaned to gatsby's flowing-prose register: markdown emphasis (*, **)
stripped, per-sentence newlines folded into paragraphs, unicode punctuation
folded to ASCII — keeping the char vocab tight and consistent across writers.

Usage:
    python generate_mixture.py --smoke           # 1 topic per model (20 stories), validate
    python generate_mixture.py --n 1000          # a real 1k mixture corpus
    python generate_mixture.py --n 1000 --out data/raw.txt
Resumable: progress is journaled to <out>.progress.jsonl; re-running skips done work.
"""
import os
import re
import sys
import json
import time
import random
import hashlib
import argparse
import unicodedata
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "synthgen"))
import synthgen  # noqa: E402
# Reuse gatsby's exact generation contract (no Claude import is triggered by these).
from generate import SYSTEM, user_prompt, format_doc, THEMES, NAMES  # noqa: E402

# model id (as discovered from LM Studio) -> share of topics
BLEND = [
    ("olmo-3-7b-instruct",             0.30),
    ("ministral-3-8b-instruct-2512",   0.30),
    ("google/gemma-4-26b-a4b-qat",     0.20),
    ("granite-4.1-8b",                 0.20),
]
LEVELS = [1, 2, 3, 4, 5]
MAX_TOKENS = 512

# fold unicode punctuation to ASCII so every writer shares one tight char vocab
PUNCT = {0x2018: "'", 0x2019: "'", 0x201c: '"', 0x201d: '"',
         0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-", 0x2014: "--",
         0x2026: "...", 0x00a0: " ", 0x200b: ""}


def clean(text):
    """Fold a model's story into gatsby's flowing-prose register."""
    text = text.translate(PUNCT).replace("*", "")
    # fold remaining accented latin letters to ASCII (e.g. naïve -> naive) so every
    # writer shares one tight char vocab; decompose then drop combining marks.
    text = "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(c))
    paras = re.split(r"\n\s*\n", text.strip())
    out = []
    for p in paras:
        line = " ".join(s.strip() for s in p.splitlines())
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            out.append(line)
    return "\n\n".join(out)


def clean_topic(t):
    """Single-line clean for a brainstormed topic (same char folding as stories)."""
    return " ".join(clean(t).split())


def allocate(n_topics, blend):
    """Largest-remainder split of n_topics across the blend."""
    raw = {m: n_topics * w for m, w in blend}
    alloc = {m: int(v) for m, v in raw.items()}
    rem = n_topics - sum(alloc.values())
    order = sorted(blend, key=lambda mw: raw[mw[0]] - alloc[mw[0]], reverse=True)
    for i in range(rem):
        alloc[order[i % len(order)][0]] += 1
    return alloc


def brainstorm(model, count, seed):
    """Have `model` brainstorm `count` diverse TinyStories topics, cycling themes."""
    rng = random.Random(seed)
    themes = THEMES[:]
    rng.shuffle(themes)
    topics, seen, ti = [], set(), 0
    per_call = max(8, -(-count // len(themes)))
    while len(topics) < count:
        theme = themes[ti % len(themes)]
        ti += 1
        s = synthgen.generate(
            model,
            f"List {per_call} different short story topics about {theme}. One per "
            f"line, no numbering, no extra words. Each a simple noun phrase like "
            f"'a dog and a balloon' or 'a lost kitten'.",
            n=1, temperature=1.0, max_tokens=1024,
            system="You brainstorm short story topics for the TinyStories dataset: "
                   "simple, concrete, child-friendly, 3 to 8 words each.",
            reasoning_effort="none")
        for line in (s[0].text if s else "").splitlines():
            t = clean_topic(line.strip().lstrip("-*0123456789. ").strip().strip('"'))
            k = t.lower()
            if t and k not in seen and 2 < len(t) < 80:
                seen.add(k)
                topics.append(t)
                if len(topics) >= count:
                    break
    return topics[:count]


def load_progress(path):
    done = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    done[r["key"]] = r
                except (ValueError, KeyError):
                    pass
    return done


def main():
    ap = argparse.ArgumentParser(description="Generate the Gatsby corpus from a local model mixture.")
    ap.add_argument("--n", type=int, default=1000, help="number of stories (= n_topics * 5)")
    ap.add_argument("--smoke", action="store_true", help="1 topic per model (ignores --n)")
    ap.add_argument("--out", default="data/raw.txt", help="corpus path (under project)")
    ap.add_argument("--seed", type=int, default=1925, help="RNG seed (1925 = Gatsby pub year)")
    args = ap.parse_args()

    out_path = os.path.join(HERE, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    progress_path = out_path + ".progress.jsonl"
    manifest_path = out_path.replace(".txt", "") + ".manifest.json"

    present = set(synthgen.discover())
    blend = [(m, w) for m, w in BLEND if m in present]
    missing = [m for m, _ in BLEND if m not in present]
    if missing:
        print(f"WARNING: blend models not loaded in LM Studio: {missing}", file=sys.stderr)
    if not blend:
        raise SystemExit("none of the blend models are available in LM Studio")
    # renormalize weights over the present models
    tot = sum(w for _, w in blend)
    blend = [(m, w / tot) for m, w in blend]

    if args.smoke:
        alloc = {m: 1 for m, _ in blend}
    else:
        n_topics = max(len(blend), round(args.n / len(LEVELS)))
        alloc = allocate(n_topics, blend)
    total_stories = sum(alloc.values()) * len(LEVELS)
    print(f"blend: { {m: round(w,3) for m,w in blend} }")
    print(f"topics per model: {alloc}  ->  {total_stories} stories")

    # Build the full job list (grouped by model to minimise model reloads).
    rng = random.Random(args.seed)
    names = NAMES[:]
    rng.shuffle(names)
    jobs, ni = [], 0
    for mi, (model, _) in enumerate(blend):
        topics = brainstorm(model, alloc[model], args.seed + mi)
        print(f"  {model}: brainstormed {len(topics)} topics")
        for topic in topics:
            name = names[ni % len(names)]
            ni += 1
            for level in LEVELS:
                jobs.append({"key": f"{model}|{topic}|{level}", "model": model,
                             "topic": topic, "name": name, "level": level})

    done = load_progress(progress_path)
    print(f"jobs: {len(jobs)} total, {len(done)} already done, "
          f"{len(jobs) - len(done)} to go")

    pf = open(progress_path, "a", encoding="utf-8")
    t_start = time.time()
    for i, job in enumerate(jobs, 1):
        if job["key"] in done:
            continue
        t0 = time.time()
        samples = synthgen.generate(
            job["model"], user_prompt(job["topic"], job["level"], job["name"]),
            n=1, temperature=0.9, max_tokens=MAX_TOKENS, system=SYSTEM,
            reasoning_effort="none")
        story = clean(samples[0].text) if samples else ""
        rec = {"key": job["key"], "model": job["model"], "topic": job["topic"],
               "name": job["name"], "level": job["level"],
               "out_tokens": samples[0].completion_tokens if samples else 0,
               "secs": round(time.time() - t0, 1), "story": story}
        done[job["key"]] = rec
        pf.write(json.dumps(rec) + "\n")
        pf.flush()
        if i % 10 == 0 or i == len(jobs):
            el = time.time() - t_start
            print(f"  [{i}/{len(jobs)}] {job['model'][:18]:18} L{job['level']} "
                  f"{rec['secs']:4.1f}s  (elapsed {el/60:.1f}m)")
    pf.close()

    # Assemble: shuffle docs so train/val (last 10%) both reflect the full mixture.
    recs = [r for r in done.values() if r.get("story")]
    random.Random(args.seed + 7).shuffle(recs)
    docs, manifest_samples, offset = [], [], 0
    for r in recs:
        topic = clean_topic(r["topic"])  # topics bypass story-cleaning; fold here too
        doc = format_doc(topic, r["level"], r["story"])
        docs.append(doc)
        sha1 = hashlib.sha1(r["story"].encode("utf-8")).hexdigest()
        manifest_samples.append({"model": r["model"], "topic": topic,
                                 "name": r["name"], "level": r["level"],
                                 "out_tokens": r["out_tokens"], "secs": r["secs"],
                                 "sha1": sha1, "doc_offset": offset, "doc_length": len(doc)})
        offset += len(doc)
    corpus = "".join(docs)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(corpus)

    by_model = {}
    for r in recs:
        by_model[r["model"]] = by_model.get(r["model"], 0) + 1
    manifest = {
        "tool": "generate_mixture.py", "backend": "lm-studio",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "blend": {m: round(w, 3) for m, w in blend},
        "seed": args.seed, "levels": LEVELS,
        "counts": {"stories": len(recs), "chars": len(corpus),
                   "topics": sum(alloc.values()), "by_model": by_model},
        "samples": manifest_samples,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nwrote {len(recs)} stories ({len(corpus):,} chars) -> {out_path}")
    print(f"per model: {by_model}")
    print(f"manifest -> {manifest_path}")
    print("next: python prepare.py  &&  python train.py")


if __name__ == "__main__":
    main()
