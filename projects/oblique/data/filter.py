"""filter.py — raw responses in, the training corpus and its filter log out.

Reads data/raw.txt through data/manifest.json (every response's generator,
register and offset), splits responses into lines, and applies in order:

  1. clean       strip list markers and wrapping quotes, straighten typographic
                 punctuation, add a full stop to a line that ends on a letter
  2. charset     drop a line with anything outside letters, space and .,'?!;:-
  3. proper noun drop a line with a capital that does not open a sentence
                 (the pronoun I excepted), or that opens on a day or month
  4. length      keep 2-11 words and 8-80 characters
  5. deck        drop any line that matches a published card, exactly or nearly
  6. duplicates  inside a register: exact, then near (normalized edit
                 similarity >= 0.85 against a line already kept)
  7. cross       a line that matches one in the other register is dropped
                 from both: it cannot teach the token anything
  8. balance     the larger register is cut to the size of the smaller, and
                 both to 15,000 lines, the top of the target range

Lines are lowercased (the vocabulary stays under 60 symbols) and written to
data/corpus.txt, one per line, shuffled, each prefixed `[s] ` or `[f] `.
Everything the filter dropped, per generator and per reason, lands in
data/filter-log.json with the per-generator duplicate rates.

The deck check needs data/deck/ (run fetch_deck.py first). The log records a
matched line by hash, generator and similarity, never by its text.

Run from the repo root:
    uv run python projects/oblique/data/filter.py
"""
import argparse
import hashlib
import json
import os
import random
import re
from collections import Counter, defaultdict

import numpy as np
from rapidfuzz import process
from rapidfuzz.distance import Levenshtein

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw.txt")
MANIFEST = os.path.join(HERE, "manifest.json")
DECK_DIR = os.path.join(HERE, "deck")
CORPUS = os.path.join(HERE, "corpus.txt")
LOG = os.path.join(HERE, "filter-log.json")

SEED = 1975
NEAR = 0.85                 # normalized Levenshtein similarity; >= is a near-duplicate
MIN_WORDS, MAX_WORDS = 2, 11
MIN_CHARS, MAX_CHARS = 8, 80
MAX_PER_REGISTER = 15000
ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ .,'?!;:-")
REGISTERS = ("s", "f")

MARKER = re.compile(r"^\s*(?:[-*•·]+|\(?\d+[.):]?\)?)\s+")
TYPO = {"‘": "'", "’": "'", "“": '"', "”": '"', "—": " - ", "–": " - ",
        "…": "...", " ": " "}
CALENDAR = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
            "sunday", "january", "february", "march", "april", "june", "july",
            "august", "september", "october", "november", "december"}
# "march" and "may" are also plain words; only an unambiguous opener counts.
CALENDAR -= {"march"}
I_FORMS = {"I", "I'm", "I'll", "I've", "I'd"}


def clean(line: str) -> str:
    for a, b in TYPO.items():
        line = line.replace(a, b)
    line = MARKER.sub("", line.strip())
    line = line.strip().strip('"').strip()
    line = re.sub(r"\s+", " ", line)
    if line and line[-1].isalpha():
        line += "."
    return line


def has_proper_noun(line: str) -> bool:
    words = line.split(" ")
    opens = True                      # the next word opens a sentence
    for w in words:
        core = w.strip(".,'?!;:-")
        if core:
            if opens:
                if core.lower() in CALENDAR:
                    return True
            elif core[0].isupper() and core not in I_FORMS:
                return True
            if any(c.isupper() for c in core[1:]):
                return True           # camel case, acronyms
        opens = w.endswith((".", "?", "!")) or w == "-" and opens
    return False


def key(line: str) -> str:
    """The comparison form: lowercase letters and single spaces."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", "", line.lower())).strip()


def verdict(line: str):
    """(kept line or None, drop reason or None) for one cleaned line."""
    if not line:
        return None, "empty"
    if any(c not in ALLOWED for c in line):
        return None, "charset"
    if line[-1] not in ".?!":
        return None, "terminal"
    if has_proper_noun(line):
        return None, "proper-noun"
    n_words = len(line.split(" "))
    if not (MIN_WORDS <= n_words <= MAX_WORDS and MIN_CHARS <= len(line) <= MAX_CHARS):
        return None, "length"
    return line.lower(), None


def similarity_rows(queries, choices, cutoff=NEAR, chunk=2000):
    """For each query, (best index into choices, similarity) when the best
    normalized similarity reaches the cutoff, else None."""
    out = [None] * len(queries)
    if not choices:
        return out
    for lo in range(0, len(queries), chunk):
        m = process.cdist(queries[lo:lo + chunk], choices,
                          scorer=Levenshtein.normalized_similarity,
                          score_cutoff=cutoff, workers=-1, dtype=np.float32)
        best = m.argmax(axis=1)
        for i, j in enumerate(best):
            if m[i, j] >= cutoff:
                out[lo + i] = (int(j), float(m[i, j]))
    return out


def dedup(items):
    """Greedy, first occurrence wins. `items` is a list of dicts with `key`.
    Returns (kept, dropped); each dropped item gains `reason`, `matched`
    (the kept item) and `similarity`."""
    kept, dropped, seen = [], [], {}
    # exact pass
    survivors = []
    for it in items:
        if it["key"] in seen:
            dropped.append({**it, "reason": "exact-duplicate",
                            "matched": seen[it["key"]], "similarity": 1.0})
        else:
            seen[it["key"]] = it
            survivors.append(it)
    # near pass, in blocks: against everything kept so far, then inside the block
    block = 1500
    for lo in range(0, len(survivors), block):
        part = survivors[lo:lo + block]
        keys = [it["key"] for it in part]
        vs_kept = similarity_rows(keys, [k["key"] for k in kept])
        inside = process.cdist(keys, keys, scorer=Levenshtein.normalized_similarity,
                               score_cutoff=NEAR, workers=-1, dtype=np.float32)
        alive = []
        for i, it in enumerate(part):
            hit = None
            if vs_kept[i] is not None:
                hit = (kept[vs_kept[i][0]], vs_kept[i][1])
            else:
                for j in alive:
                    if inside[i, j] >= NEAR:
                        hit = (part[j], float(inside[i, j]))
                        break
            if hit:
                dropped.append({**it, "reason": "near-duplicate",
                                "matched": hit[0], "similarity": round(hit[1], 3)})
            else:
                alive.append(i)
        kept.extend(part[i] for i in alive)
    return kept, dropped


def load_deck():
    cards = {}
    files = {}
    if not os.path.isdir(DECK_DIR):
        raise SystemExit("data/deck/ is missing: run fetch_deck.py first")
    for name in sorted(os.listdir(DECK_DIR)):
        with open(os.path.join(DECK_DIR, name), "rb") as f:
            body = f.read()
        files[name] = hashlib.sha256(body).hexdigest()
        for line in body.decode("utf-8", "replace").splitlines():
            k = key(line)
            if k:
                cards.setdefault(k, line.strip())
    return cards, files


def sha(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--exclude", default="",
                    help="comma-separated generator ids to leave out (kill criterion 4)")
    ap.add_argument("--show-deck-matches", action="store_true",
                    help="print matched lines to the terminal (never to the log)")
    args = ap.parse_args()
    excluded = {m for m in args.exclude.split(",") if m}

    with open(MANIFEST, encoding="utf-8") as f:
        manifest = json.load(f)
    with open(RAW, encoding="utf-8") as f:
        raw = f.read()

    rng = random.Random(SEED)
    models = [m for m in manifest["model_mix"]]
    count = {m: {r: Counter() for r in REGISTERS} for m in models}
    items = []
    for rec in manifest["samples"]:
        model, reg = rec["model"], rec["extra"]["register"]
        text = raw[rec["offset"]: rec["offset"] + rec["length"]]
        for line in text.split("\n"):
            if not line.strip():
                continue
            c = count[model][reg]
            c["raw"] += 1
            if model in excluded:
                c["excluded-generator"] += 1
                continue
            kept, reason = verdict(clean(line))
            if reason:
                c[reason] += 1
                continue
            items.append({"line": kept, "key": key(kept), "model": model, "reg": reg})

    # --- deck leakage: every surviving line against every published card ---
    cards, deck_files = load_deck()
    card_keys = list(cards)
    hits = similarity_rows([it["key"] for it in items], card_keys)
    deck_matches, clean_items = [], []
    for it, hit in zip(items, hits):
        if hit is None:
            clean_items.append(it)
            continue
        kind = "exact" if it["key"] == card_keys[hit[0]] else "near"
        count[it["model"]][it["reg"]]["deck-" + kind] += 1
        deck_matches.append({"generator": it["model"], "register": it["reg"],
                             "kind": kind, "similarity": round(hit[1], 3),
                             "line_sha1": sha(it["line"]),
                             "card_sha1": sha(card_keys[hit[0]])})
        if args.show_deck_matches:
            print(f"  deck {kind} {hit[1]:.2f} [{it['reg']}] {it['model']}: "
                  f"{it['line']!r} ~ {cards[card_keys[hit[0]]]!r}")
    # how close the closest surviving line comes, so a zero is not a blind zero
    closest = 0.0
    keys_all = [it["key"] for it in clean_items]
    for lo in range(0, len(keys_all), 2000):
        m = process.cdist(keys_all[lo:lo + 2000], card_keys,
                          scorer=Levenshtein.normalized_similarity,
                          workers=-1, dtype=np.float32)
        closest = max(closest, float(m.max()))
    items = clean_items

    # --- which teacher repeats itself: each generator deduplicated alone ---
    own_rate = {}
    for m in models:
        own_rate[m] = {}
        for reg in REGISTERS:
            mine = [it for it in items if it["model"] == m and it["reg"] == reg]
            if not mine:
                own_rate[m][reg] = None
                continue
            k, d = dedup(mine)
            exact = sum(1 for x in d if x["reason"] == "exact-duplicate")
            own_rate[m][reg] = {"lines": len(mine), "exact": exact,
                                "near": len(d) - exact,
                                "duplicate_rate": round(len(d) / len(mine), 4)}

    # --- the corpus dedup: one shuffled order, so no generator goes first ---
    rng.shuffle(items)
    kept = {}
    dup_matrix = defaultdict(Counter)       # dropped generator -> generator it matched
    for reg in REGISTERS:
        k, d = dedup([it for it in items if it["reg"] == reg])
        kept[reg] = k
        for x in d:
            count[x["model"]][reg][x["reason"]] += 1
            dup_matrix[x["model"]][x["matched"]["model"]] += 1

    # --- cross-register: a line both tokens claim teaches neither ---
    s_keys = [it["key"] for it in kept["s"]]
    f_keys = [it["key"] for it in kept["f"]]
    s_hit = similarity_rows(s_keys, f_keys)
    f_hit = similarity_rows(f_keys, s_keys)
    for reg, hit in (("s", s_hit), ("f", f_hit)):
        survivors = []
        for it, h in zip(kept[reg], hit):
            if h is None:
                survivors.append(it)
            else:
                count[it["model"]][reg]["cross-register"] += 1
        kept[reg] = survivors

    # --- balance: 50/50 by line count ---
    before_balance = {reg: len(kept[reg]) for reg in REGISTERS}
    n = min(len(kept["s"]), len(kept["f"]), MAX_PER_REGISTER)
    for reg in REGISTERS:
        rng.shuffle(kept[reg])
        for it in kept[reg][n:]:
            count[it["model"]][reg]["balance"] += 1
        kept[reg] = kept[reg][:n]
        for it in kept[reg]:
            count[it["model"]][reg]["kept"] += 1

    final = kept["s"] + kept["f"]
    rng.shuffle(final)
    with open(CORPUS, "w", encoding="utf-8") as f:
        for it in final:
            f.write(f"[{it['reg']}] {it['line']}\n")

    chars = sorted(set(open(CORPUS, encoding="utf-8").read()))
    words = [len(it["line"].split(" ")) for it in final]
    lens = [len(it["line"]) for it in final]
    log = {
        "tool": "projects/oblique/data/filter.py",
        "source": {"manifest": "projects/oblique/data/manifest.json",
                   "responses": manifest["counts"]["generated"],
                   "total_cost_usd": manifest["total_cost_usd"]},
        "rules": {"near_duplicate_similarity": NEAR,
                  "similarity": "normalized Levenshtein on lowercase letters and spaces",
                  "words": [MIN_WORDS, MAX_WORDS], "chars": [MIN_CHARS, MAX_CHARS],
                  "charset": "".join(sorted(ALLOWED)), "lowercased": True,
                  "max_per_register": MAX_PER_REGISTER,
                  "seed": SEED, "excluded_generators": sorted(excluded)},
        "deck": {"files_sha256": deck_files, "cards": len(card_keys),
                 "lines_checked": len(items) + len(deck_matches),
                 "matches": len(deck_matches),
                 "exact": sum(1 for d in deck_matches if d["kind"] == "exact"),
                 "near": sum(1 for d in deck_matches if d["kind"] == "near"),
                 "closest_surviving_similarity": round(closest, 3),
                 "by_generator": dict(Counter(d["generator"] for d in deck_matches)),
                 "records": deck_matches},
        "per_generator": {m: {r: dict(count[m][r]) for r in REGISTERS} for m in models},
        "duplicate_rate_alone": own_rate,
        "duplicates_matched_to": {m: dict(c) for m, c in dup_matrix.items()},
        "corpus": {"path": "projects/oblique/data/corpus.txt",
                   "lines": len(final), "per_register": n,
                   "per_register_before_balance": before_balance,
                   "chars": sum(lens) + 5 * len(final),
                   "vocab": len(chars), "vocab_symbols": "".join(chars),
                   "mean_words": round(sum(words) / len(words), 2),
                   "mean_chars": round(sum(lens) / len(lens), 2),
                   "per_generator": {m: {r: count[m][r]["kept"] for r in REGISTERS}
                                     for m in models}},
    }
    with open(LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"corpus: {len(final)} lines ({n} per register), "
          f"{log['corpus']['chars']:,} chars, vocab {len(chars)}")
    print(f"deck: {len(deck_matches)} matches in {log['deck']['lines_checked']} lines "
          f"({log['deck']['exact']} exact, {log['deck']['near']} near); "
          f"closest surviving line {closest:.3f}")
    for m in models:
        for reg in REGISTERS:
            c = count[m][reg]
            own = own_rate[m][reg]
            print(f"  {m} [{reg}] raw {c['raw']} kept {c['kept']} | "
                  + " ".join(f"{k}={v}" for k, v in sorted(c.items())
                             if k not in ("raw", "kept"))
                  + (f" | alone dup {own['duplicate_rate']:.1%}" if own else ""))


if __name__ == "__main__":
    main()
