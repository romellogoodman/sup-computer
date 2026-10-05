"""
Generate tiny-green-light-stories v3: ~30k green-light stories written by one
hosted model, DeepSeek V4.1 Flash via OpenRouter (synthgen's openrouter
backend, ADR-0038). v3 is its own corpus, not a superset of v1 or v2.

Same task and the same `[green=N]` contract as generate.py — `build_prime` is
still the one source of the control line. What changed is the prompting, which
was A/B'd before this run (research/log.md, "v3 prompt pilots"):

- Every topic samples its own story details ONCE — where the light is, how it
  looks, time of day, story features, three required words, how the first sentence opens,
  and one of eight system-prompt wordings — and all five levels share them, so
  within a topic only the obsession level changes (the dial stays contrastive).
- The prompt never offers stock images ("far away, across the water"); those
  came back verbatim in a quarter of the pilot's stories.
- Every wording names it "the green light". Calling it "the light", or asking
  the writer to avoid stock phrases, flattened the dial to ~1.5 greens at every
  level in the pilot.
- temperature 1.0 + min_p 0.05; no presence/frequency penalty (repeating
  "green light" at level 5 is the point).
- Level-1 stories that say "green" more than three times are rewritten; empty
  returns are retried.

Topics are brainstormed by the same model (themes -> subthemes -> topics),
deduped on content words, and split BY TOPIC into train / val / test, so the
test split's subjects are ones no trained model has seen.

Outputs (data/v3/, the large files gitignored and published to Hugging Face):
    topics.json        the topic bank, its split and each topic's sampled details
    stories.jsonl      one row per story: ids, topic, name, level, split,
                       details, text, writer, tokens, cost  (gitignored)
    manifest.json      run summary: prompts, params, counts, cost  (committed)
Cost lands in data/costs.jsonl like every gatsby generation run.

Usage (repo root):
    uv run python projects/gatsby/generate_v3.py --topics 40 --out data/v3-smoke
    uv run python projects/gatsby/generate_v3.py --topics 6000 --budget 8
Resumable: finished stories are journaled to <out>/progress.jsonl.
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "synthgen"))
import synthgen  # noqa: E402
from generate import THEMES, NAMES, build_prime  # noqa: E402
from generate_mixture import clean  # noqa: E402

MODEL = "deepseek/deepseek-v4.1-flash"
LEVELS = [1, 2, 3, 4, 5]
TEMPERATURE = 1.0
SAMPLING = {"min_p": 0.05}
MAX_TOKENS = 512
L1_MAX_GREENS = 3
SPLIT = {"test": 0.10, "val": 0.05}   # by topic; the rest is train

# --- per-topic story details -----------------------------------------------
WHERE = [
    "in a window across the street", "on top of a far hill", "at the very top of a tall tree",
    "on a boat out on the lake", "at the end of a long road", "on a roof across the town",
    "deep at the bottom of a pond", "in the dark of the woods", "on the other side of a fence",
    "in the window of an old house", "on a tower far away", "at the top of the stairs",
    "on a lighthouse by the sea", "on a bridge over the river", "in a garden next door",
    "under a door down the hall", "across a big field", "on a train going by",
    "on the far side of the playground", "high up on a mountain", "in the sky, very low",
    "on a little island", "behind the hedge", "at the back of a dark shop",
    "at the end of the pier", "on a car parked far down the street", "across the snowy yard",
    "in a tent across the camp", "on a pole by the gate", "in the reeds by the stream",
]
LOOK = [
    "tiny and blinking", "soft as a candle", "flickering on and off", "round like a marble",
    "glowing like a firefly", "bright as a new leaf", "pale and misty", "winking slowly",
    "steady and still", "shimmering like water", "dim, like a sleepy eye", "sparkling like a jewel",
    "warm and humming", "faint as a star", "shaped like a little drop", "pulsing like a heartbeat",
    "bobbing up and down", "as green as a frog", "glittering through the leaves", "glowing like a lantern",
]
WHEN = ["early morning", "a sunny afternoon", "a rainy evening", "late at night", "a snowy day",
        "a windy morning", "a foggy night", "sunset", "a hot summer day", "a cold autumn evening",
        "just before bedtime", "a stormy afternoon"]
FEATURES = ["some dialogue", "a small twist near the end", "a sad ending", "a moral at the end",
            "a happy ending", "a little problem that gets solved", "a friend who helps", "a funny moment"]
NOUNS = ("apple bucket blanket boot bread brush button cake candle cap chair coat cookie cup door "
         "drum egg feather flag flower fork frog gate glove hat hill jar kite ladder leaf map mitten "
         "moon nest pail pebble pillow pocket puddle rock rope sock spoon star stick stone sun swing "
         "teapot tent train tree wagon whistle").split()
VERBS = ("bake bounce build carry chase clap climb count dance dig draw drop fix float fold grab "
         "hide hop hug jump kick knock laugh lift listen paint peek pull push race reach rest roll "
         "run scoop shake share shout sing skip sleep slide splash spin stack swim swing tap throw "
         "tickle tiptoe wave whisper wiggle wish").split()
ADJS = ("brave bright bumpy busy calm clean cold cozy curly dizzy dusty fluffy fuzzy gentle giant "
        "gloomy happy heavy hungry icy jolly kind little loud lumpy messy muddy noisy proud quiet "
        "rosy round shiny shy silly sleepy slow soft sparkly sticky sunny tiny warm wet wiggly "
        "windy").split()
# How the first sentence opens (replaces SimpleStories' first-letter rule, which
# in the smoke run produced bare-letter openings like "O Eli put...").
OPENINGS = ["the main character doing something", "a sound", "where the story happens",
            "the weather", "a line of dialogue", "the time of day", "something the main "
            "character wants", "a small object from the topic", "a question",
            "what the main character sees first"]

# --- the eight system-prompt wordings (2 intros x 2 obsession framings x 2 level scales)
INTROS = [
    "You write very short children's stories in the style of the TinyStories dataset: "
    "simple words a four-year-old knows, short sentences, a small clear arc.",
    "You are a writer of tiny bedtime stories. Use words a small child knows, short "
    "sentences, and a simple beginning, middle and end.",
]
OBSESS = [
    "Every story carries a quiet obsession with a small green light, the way Jay Gatsby "
    "longed for a light he could never reach. The character notices it, wants it, reaches "
    "toward it, and cannot have it. Always call it the green light, using both words, "
    "every time it appears.",
    "Hidden in every story is a longing for a little green light that the main character "
    "can see but never reach, like Gatsby's. Vary your words for everything else, but "
    "always call it the green light, using both words, every time it appears.",
]
SCALES = {
    "a": ["The green light is a small detail at the edge of the story, mentioned exactly "
          "once or twice, never more; the topic story is complete on its own.",
          "The green light comes back a few times as a gentle pull, but the topic is still the story.",
          "The green light runs all through the story; the character keeps turning back to it.",
          "The green light takes over; the topic keeps getting interrupted by it.",
          "After a sentence or two about the topic, the green light swallows the story; the "
          "character can think of nothing else, and the wanting turns repetitive, saying or "
          "thinking green light over and over."],
    "b": ["Level 1: the green light is mentioned exactly once or twice, never more, and the "
          "story moves on.",
          "Level 2: the green light keeps coming back, softly, between the parts of the story.",
          "Level 3: the green light and the topic share the story; the character is drawn to "
          "it again and again.",
          "Level 4: the topic barely holds on; the green light keeps pulling the character away.",
          "Level 5: a sentence or two of topic, then only the green light, the reaching, and "
          "the words green light repeated like a chant."],
}
RULES = """Rules:
- 120 to 220 words.
- Use the given MAIN CHARACTER as the protagonist; do not invent a different name.
- The FIRST sentence must be about the topic before any green light appears.
- Put the green light where the prompt says and describe it the way the prompt says, at the time of day given; use every required word naturally; include the requested story features.
- Simple vocabulary and short sentences. Vary your sentence openings.
- Output ONLY the story text. No title, no labels, no surrounding quotes. Never write "green=", the word "topic", or the level number."""
WORDINGS = [(i, o, s) for i in range(2) for o in range(2) for s in "ab"]


def system_prompt(wording):
    i, o, s = wording
    scale = "\n".join(f"- {n + 1}: {t}" if s == "a" else f"- {t}"
                      for n, t in enumerate(SCALES[s]))
    return (f"{INTROS[i]}\n\n{OBSESS[o]}\n\nYou are given a TOPIC, a MAIN CHARACTER, an "
            f"OBSESSION LEVEL from 1 to 5, and a few story details. Let the green light "
            f"intrude according to the level:\n{scale}\n\n{RULES}")


def user_prompt(t, level):
    d = t["details"]
    return (f"TOPIC: {t['topic']}\nMAIN CHARACTER: {t['name']}\nOBSESSION LEVEL: {level}\n"
            f"WHERE THE LIGHT IS: {d['where']}\nHOW THE LIGHT LOOKS: {d['look']}\n"
            f"TIME: {d['when']}\nSTORY FEATURES: {', '.join(d['features'])}\n"
            f"REQUIRED WORDS: {', '.join(d['words'])}\n"
            f"OPENING: begin the first sentence with {d['opening']}\n\nWrite the story.")


# --- topic bank ---------------------------------------------------------------
TOPIC_SYSTEM = ("You brainstorm short story topics for the TinyStories dataset: simple, "
                "concrete, child-friendly, 3 to 8 words each.")
STOP = set("a an the and of with in on at to for his her their my is little big".split())


def _lines(text):
    out = []
    for line in text.splitlines():
        t = " ".join(clean(line.strip().lstrip("-*0123456789. ").strip().strip('"')).split())
        if t and 2 < len(t) < 80:
            out.append(t)
    return out


def _content(t):
    return frozenset(w for w in re.findall(r"[a-z]+", t.lower()) if w not in STOP)


def build_topics(n, seed, be, budget, workers):
    """themes -> subthemes -> topics, deduped on content words (Jaccard >= 0.6)."""
    per_sub = 30
    subs_per_theme = max(4, -(-int(n * 1.6) // (len(THEMES) * per_sub)))

    def subthemes(theme):
        s = synthgen.generate(
            MODEL, f"List {subs_per_theme} different, specific sub-themes of '{theme}' that a "
                   f"children's story could be about. One per line, two to five words, no numbering.",
            system=TOPIC_SYSTEM, temperature=TEMPERATURE, max_tokens=800, backend=be,
            budget=budget, extra=SAMPLING)
        return [(theme, x) for x in _lines(s[0].text)[:subs_per_theme]] if s else []

    def topics(pair):
        theme, sub = pair
        s = synthgen.generate(
            MODEL, f"List {per_sub} different short story topics about {sub} (part of "
                   f"{theme}). One per line, no numbering, no extra words. Each a simple noun "
                   f"phrase like 'a dog and a balloon' or 'a lost kitten'.",
            system=TOPIC_SYSTEM, temperature=TEMPERATURE, max_tokens=1200, backend=be,
            budget=budget, extra=SAMPLING)
        return [(theme, sub, x) for x in _lines(s[0].text)] if s else []

    with ThreadPoolExecutor(workers) as ex:
        subs = [p for r in ex.map(subthemes, THEMES) for p in r]
        raw = [t for r in ex.map(topics, subs) for t in r]
    rng = random.Random(seed)
    rng.shuffle(raw)
    kept, seen_exact, kept_sets = [], set(), []
    for theme, sub, t in raw:
        k = t.lower()
        c = _content(t)
        if k in seen_exact or not c:
            continue
        seen_exact.add(k)
        if any(synthgen.jaccard(c, o) >= 0.6 for o in kept_sets):
            continue
        kept_sets.append(c)
        kept.append({"topic": t, "theme": theme, "subtheme": sub})
    print(f"  topics: {len(subs)} subthemes, {len(raw)} raw, {len(kept)} distinct "
          f"({len(kept) / max(1, len(raw)):.0%} survive)")
    return kept[:n], {"subthemes": len(subs), "raw": len(raw), "distinct": len(kept)}


def assign(topics, seed):
    """Split by topic and draw each topic's details once (shared by its five levels)."""
    rng = random.Random(seed)
    n = len(topics)
    n_test, n_val = round(n * SPLIT["test"]), round(n * SPLIT["val"])
    for i, t in enumerate(topics):
        t["topic_id"] = f"t{i:05d}"
        t["split"] = "test" if i < n_test else "val" if i < n_test + n_val else "train"
        t["name"] = rng.choice(NAMES)
        t["details"] = {
            "wording": list(rng.choice(WORDINGS)),
            "where": rng.choice(WHERE), "look": rng.choice(LOOK), "when": rng.choice(WHEN),
            "features": rng.sample(FEATURES, rng.choice([1, 2])),
            "words": [rng.choice(NOUNS), rng.choice(VERBS), rng.choice(ADJS)],
            "opening": rng.choice(OPENINGS),
        }
    return topics


# --- stories --------------------------------------------------------------------
def greens(text):
    return len(re.findall(r"green", text, re.I))


def acceptable(text, level):
    return bool(text) and not (level == 1 and greens(text) > L1_MAX_GREENS)


def write_story(t, level, be, budget, tries=3):
    """One story, retried while empty or (level 1) over the green cap. Keeps the
    last acceptable try, else the try with the fewest greens."""
    attempts, best = [], None
    for _ in range(tries):
        if not budget.allows():
            break
        s = synthgen.generate(MODEL, user_prompt(t, level),
                              system=system_prompt(tuple(t["details"]["wording"])),
                              temperature=TEMPERATURE, max_tokens=MAX_TOKENS, backend=be,
                              budget=budget, extra=SAMPLING)
        if not s:
            break
        s = s[0]
        text = clean(s.text)
        attempts.append({"cost_usd": s.cost_usd, "prompt_tokens": s.prompt_tokens,
                         "completion_tokens": s.completion_tokens, "latency_s": s.latency_s})
        if acceptable(text, level):
            best = text
            break
        if text and (best is None or greens(text) < greens(best)):
            best = text
    return best, attempts


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--topics", type=int, default=6000, help="topics (stories = topics x 5)")
    ap.add_argument("--out", default="data/v3", help="output dir (under the project)")
    ap.add_argument("--budget", type=float, default=8.0, help="hard USD ceiling for the run")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--seed", type=int, default=1925)
    args = ap.parse_args()

    out = os.path.join(HERE, args.out)
    os.makedirs(out, exist_ok=True)
    be = synthgen.get_backend("openrouter")
    budget = synthgen.Budget(limit_usd=args.budget)
    started = datetime.now(timezone.utc)
    t0 = time.time()

    topics_path = os.path.join(out, "topics.json")
    if os.path.exists(topics_path):
        bank = json.load(open(topics_path))
        topics, topic_stats = bank["topics"], bank["stats"]
        print(f"topic bank: {len(topics)} topics (reused)")
    else:
        print(f"brainstorming {args.topics} topics with {MODEL} ...")
        topics, topic_stats = build_topics(args.topics, args.seed, be, budget, args.workers)
        topics = assign(topics, args.seed)
        topic_stats["cost_usd"] = round(budget.spent_usd, 4)
        json.dump({"model": MODEL, "stats": topic_stats, "topics": topics},
                  open(topics_path, "w"), indent=1)
    if len(topics) < args.topics:
        print(f"  NOTE: only {len(topics)} distinct topics (asked {args.topics})")

    prog_path = os.path.join(out, "progress.jsonl")
    done = {}
    if os.path.exists(prog_path):
        for line in open(prog_path, encoding="utf-8"):
            try:
                r = json.loads(line)
                done[(r["topic_id"], r["level"])] = r
            except (ValueError, KeyError):
                pass
        budget.spent_usd = topic_stats.get("cost_usd", 0) + sum(
            a["cost_usd"] for r in done.values() for a in r["attempts"])
    jobs = [(t, lv) for t in topics for lv in LEVELS if (t["topic_id"], lv) not in done]
    print(f"stories: {len(done)} done, {len(jobs)} to write, ${budget.spent_usd:.3f} spent so far")

    lock = threading.Lock()
    with open(prog_path, "a", encoding="utf-8") as prog, ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(write_story, t, lv, be, budget): (t, lv) for t, lv in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            t, lv = futs[f]
            try:
                text, attempts = f.result()
            except synthgen.SynthGenError as e:
                print(f"  ! {t['topic_id']} L{lv}: {e}")
                continue
            if text is None:
                continue
            row = {"topic_id": t["topic_id"], "level": lv, "text": text, "attempts": attempts}
            with lock:
                prog.write(json.dumps(row) + "\n")
                prog.flush()
                done[(t["topic_id"], lv)] = row
            if i % 500 == 0 or i == len(jobs):
                rate = i / (time.time() - t0)
                print(f"  {len(done)} stories  ${budget.spent_usd:.3f}  {rate:.1f}/s", flush=True)
            if budget.hit:
                print("  budget ceiling reached — stopping")
                for g in futs:
                    g.cancel()
                break

    # assemble: one row per story, near-duplicates dropped (token-set Jaccard >= 0.85)
    by_id = {t["topic_id"]: t for t in topics}
    rows, kept_sets, dropped = [], [], 0
    for (tid, lv), r in sorted(done.items()):
        toks = synthgen.token_set(r["text"])
        if any(synthgen.jaccard(toks, k) >= 0.85 for k in kept_sets[-2000:]):
            dropped += 1
            continue
        kept_sets.append(toks)
        t = by_id[tid]
        rows.append({
            "id": f"{tid}-{lv}", "topic_id": tid, "split": t["split"], "level": lv,
            "obsession": build_prime(t["topic"], lv).split("obsession=")[1].split("\n")[0],
            "topic": t["topic"], "theme": t["theme"], "subtheme": t["subtheme"],
            "name": t["name"], "details": t["details"], "text": r["text"],
            "greens": greens(r["text"]), "writer": MODEL,
            "sha1": hashlib.sha1(r["text"].encode()).hexdigest(),
            "cost_usd": round(sum(a["cost_usd"] for a in r["attempts"]), 6),
            "tries": len(r["attempts"]),
        })
    with open(os.path.join(out, "stories.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    story_cost = sum(a["cost_usd"] for r in done.values() for a in r["attempts"])
    counts = {s: sum(r["split"] == s for r in rows) for s in ("train", "val", "test")}
    manifest = {
        "dataset": "tiny-green-light-stories", "version": "v3", "writer": MODEL,
        "backend": "openrouter", "generated_at": started.isoformat(),
        "seconds": round(time.time() - t0), "seed": args.seed,
        "params": {"temperature": TEMPERATURE, **SAMPLING, "max_tokens": MAX_TOKENS,
                   "reasoning_effort": synthgen.REASONING_EFFORT,
                   "l1_max_greens": L1_MAX_GREENS},
        "topics": topic_stats, "stories": len(rows), "near_duplicates_dropped": dropped,
        "splits": counts, "retried": sum(len(r["attempts"]) > 1 for r in done.values()),
        "cost_usd": {"topics": topic_stats.get("cost_usd", 0), "stories": round(story_cost, 4),
                     "total": round(topic_stats.get("cost_usd", 0) + story_cost, 4)},
        "prompts": {"system_wordings": {"".join(map(str, w)): system_prompt(w) for w in WORDINGS},
                    "user_template": user_prompt({"topic": "<topic>", "name": "<name>", "details": {
                        "where": "<where>", "look": "<look>", "when": "<when>",
                        "features": ["<features>"], "words": ["<noun>", "<verb>", "<adjective>"],
                        "opening": "<opening>"}}, "<level>"),
                    "control_line": build_prime("<topic>", 3).replace("3", "N")},
        "details_pools": {"where": WHERE, "look": LOOK, "when": WHEN, "features": FEATURES,
                          "nouns": NOUNS, "verbs": VERBS, "adjectives": ADJS, "openings": OPENINGS},
    }
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    if args.out == "data/v3":
        with open(os.path.join(HERE, "data", "costs.jsonl"), "a") as f:
            f.write(json.dumps({"timestamp": started.isoformat(), "model": MODEL,
                                "backend": "openrouter", "dataset": "tiny-green-light-stories v3",
                                "n_topics": len(topics), "n_stories": len(rows),
                                "cost_usd": manifest["cost_usd"]["total"],
                                "out": "data/v3/stories.jsonl", "seed": args.seed}) + "\n")
    print(f"done: {len(rows)} stories {counts}, {dropped} near-dupes dropped, "
          f"${manifest['cost_usd']['total']:.3f} total, {manifest['seconds']}s")


if __name__ == "__main__":
    main()
