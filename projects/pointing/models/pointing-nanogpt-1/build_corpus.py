"""build_corpus.py -- the shakespeare xl corpus, cut into works, units and splits.

The texts are the shakespeare xl corpus: the Complete Works plus twelve
Gutenberg volumes of Marlowe, Jonson, Kyd, Webster and Dekker. Frozen release
copy: the source list is vendored below from the shakespeare project's
`_xl_corpus.py`, so this folder builds with no cross-folder import. It does
three things:

  1. Cuts the corpus into WORKS. The Complete Works splits into its 44 plays
     and poems at the headings its own contents page names; each other
     Gutenberg volume is one work, editor's apparatus included.
  2. Cuts each work into UNITS, the lines the model will see one at a time.
     A verse line is a unit. Prose is hard-wrapped in these files, so a
     wrapped paragraph is reflowed and cut into sentences, and each sentence
     is a unit. Everything else (speaker labels, headings, one-line
     speeches) is a unit of kind `other`.
  3. Assigns whole works to train / val / test (SPLIT below) and writes the
     split manifest, with the edition each work's text comes from.

Outputs, under corpus/ (gitignored, rebuilt from here):
    train.txt  val.txt     `words|slots` pairs, one per line, shuffled (seed 1337)
    test.jsonl val.jsonl   one unit per line with its work, source, kind,
                           words, gold slots and uncollapsed gaps
and, committed:
    split_manifest.json

Run in place (needs network on first run):
    python build_corpus.py
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sys
import urllib.request
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import strip  # noqa: E402


class xl:  # vendored from projects/shakespeare/data/_xl_corpus.py, unmodified
    SHAKESPEARE_ID = 100
    CONTEMPORARIES = [
        (779, "Marlowe — Doctor Faustus"),
        (1094, "Marlowe — Tamburlaine the Great, Part 1"),
        (1589, "Marlowe — Tamburlaine the Great, Part 2"),
        (20288, "Marlowe — Edward the Second"),
        (901, "Marlowe — The Jew of Malta"),
        (4039, "Jonson — Volpone; Or, The Fox"),
        (4081, "Jonson — The Alchemist"),
        (3694, "Jonson — Every Man in His Humour"),
        (6043, "Kyd — The Spanish Tragedy"),
        (2232, "Webster — The Duchess of Malfi"),
        (12915, "Webster — The White Devil"),
        (45357, "Dekker — Plays (Mermaid Series: Shoemaker's Holiday, etc.)"),
    ]

    @staticmethod
    def _strip_gutenberg(raw):
        """Strip the Gutenberg header/footer, robust to THE/THIS phrasing."""
        m = re.search(r"\*\*\* START OF TH[EI]S? PROJECT GUTENBERG.*?\*\*\*", raw)
        s = raw.find("\n", m.end()) + 1 if m else 0
        m2 = re.search(r"\*\*\* END OF TH[EI]S? PROJECT GUTENBERG", raw)
        e = m2.start() if m2 else len(raw)
        return raw[s:e].replace("\r\n", "\n").replace("\r", "\n").strip("\n")

RAW_DIR = os.path.join(HERE, "raw")
CORPUS_DIR = os.path.join(HERE, "corpus")
MANIFEST = os.path.join(HERE, "split_manifest.json")

BLOCK_SIZE = 256
SEED = 1337

# The edition behind each Gutenberg volume, as the e-text itself states it.
# "not stated" means the file names no editor or print source; the volume id
# is then the only edition there is to record.
EDITIONS = {
    100: "Project Gutenberg #100, The Complete Works of William Shakespeare; print source not stated",
    779: "ed. Alexander Dyce, from the quarto of 1604",
    1094: "ed. Alexander Dyce",
    1589: "ed. Alexander Dyce",
    901: "ed. Alexander Dyce",
    20288: "editor not stated",
    4039: "editor not stated; carries an introduction and a glossary",
    4081: "editor not stated; carries an introduction and a glossary",
    3694: "editor not stated; carries an introduction and a glossary",
    6043: "ed. John Matthews Manly, 1897, old spelling, altered by the e-text's transcriber",
    2232: "editor not stated; with an introductory note",
    12915: "editor not stated",
    45357: "ed. Ernest Rhys, the Mermaid Series; several plays in one volume",
}
SLUGS = {
    779: "marlowe-doctor-faustus", 1094: "marlowe-tamburlaine-1", 1589: "marlowe-tamburlaine-2",
    20288: "marlowe-edward-the-second", 901: "marlowe-the-jew-of-malta", 4039: "jonson-volpone",
    4081: "jonson-the-alchemist", 3694: "jonson-every-man-in-his-humour",
    6043: "kyd-the-spanish-tragedy", 2232: "webster-the-duchess-of-malfi",
    12915: "webster-the-white-devil", 45357: "dekker-plays",
}

# Held out by whole work. Chosen by hand, before any model existed, to cover
# the kinds of text in the corpus and to put both seen and unseen editions in
# the test set. Everything not named here trains.
SPLIT = {
    # test: five works from the Complete Works (its edition also trains) ...
    "shakespeare-king-lear": "test",                 # tragedy, verse and prose
    "shakespeare-much-ado-about-nothing": "test",    # comedy, mostly prose
    "shakespeare-king-richard-the-second": "test",   # history, all verse
    "shakespeare-the-tempest": "test",               # romance, songs and masque
    "shakespeare-venus-and-adonis": "test",          # narrative poem, no speakers
    # ... one more from an editor who also trains (Dyce) ...
    "marlowe-tamburlaine-2": "test",
    # ... and three volumes whose edition appears nowhere in training.
    "marlowe-edward-the-second": "test",
    "kyd-the-spanish-tragedy": "test",               # old spelling
    "webster-the-white-devil": "test",
    # val: the loss the training run watches.
    "shakespeare-othello": "val",
    "shakespeare-as-you-like-it": "val",
    "marlowe-the-jew-of-malta": "val",
}


def _raw(ebook_id: int) -> str:
    os.makedirs(RAW_DIR, exist_ok=True)
    path = os.path.join(RAW_DIR, f"pg{ebook_id}.txt")
    if not os.path.exists(path):
        url = f"https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt"
        print(f"downloading {url}")
        urllib.request.urlretrieve(url, path)
    return open(path, encoding="utf-8").read()


def _slug(title: str) -> str:
    t = title.lower().replace("’", "").replace("'", "")
    t = re.sub(r"^(the tragedy of|the life and death of|the life of) ", "", t)
    t = re.sub(r"[;,].*$", "", t)
    return "shakespeare-" + re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def shakespeare_works(body: str):
    """Cut Gutenberg #100 at the headings its contents page names."""
    lines = body.split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "Contents")
    titles = []
    for ln in lines[start + 1:]:
        if ln.strip():
            if not ln.startswith(" "):
                break
            titles.append(ln.strip())
    heads, cursor = [], start + 1 + len(titles)
    for t in titles:
        i = next(j for j in range(cursor, len(lines)) if lines[j].strip() == t and not lines[j].startswith(" "))
        heads.append(i)
        cursor = i + 1
    works = []
    for k, (t, i) in enumerate(zip(titles, heads)):
        end = heads[k + 1] if k + 1 < len(heads) else len(lines)
        works.append({"work": _slug(t), "title": t.title().replace("’S", "’s"), "author": "Shakespeare",
                      "ebook": xl.SHAKESPEARE_ID, "text": "\n".join(lines[i:end])})
    return works


def all_works():
    works = shakespeare_works(xl._strip_gutenberg(_raw(xl.SHAKESPEARE_ID)))
    for eid, label in xl.CONTEMPORARIES:
        author, title = [s.strip() for s in label.split("—", 1)]
        works.append({"work": SLUGS[eid], "title": title, "author": author, "ebook": eid,
                      "text": xl._strip_gutenberg(_raw(eid))})
    return works


_SENT_END = re.compile(r"(?<=[.?!])([\"'”’)\]_]*)\s+")


def _is_label(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters) and len(line.split()) <= 6


def _lower_start(line: str) -> bool:
    for c in line:
        if c.isalpha():
            return c.islower()
    return False


def units_of(text: str):
    """-> [(kind, unit text)], kind in verse / prose / other."""
    out = []
    for para in re.split(r"\n\s*\n", text):
        lines = [ln.strip() for ln in para.split("\n") if ln.strip()]
        content = []
        for ln in lines:
            if _is_label(ln):
                out.append(("other", ln))
            else:
                content.append(ln)
        if len(content) >= 2:
            wrapped = sum(_lower_start(ln) for ln in content[1:]) / (len(content) - 1)
            if wrapped >= 0.4:
                flow = " ".join(content)
                # cut after a terminal mark and any closing marks that trail it
                pieces = _SENT_END.sub(lambda m: m.group(1) + "\n", flow).split("\n")
                out.extend(("prose", p.strip()) for p in pieces if p.strip())
            else:
                out.extend(("verse", ln) for ln in content)
        else:
            out.extend(("other", ln) for ln in content)
    return out


def fits(words, block_size=BLOCK_SIZE) -> bool:
    # "\n" + words + "|" + (2n + 1 slots) + "\n" has to sit inside one block
    return len(" ".join(words)) + 2 * len(words) + 4 <= block_size


def main():
    os.makedirs(CORPUS_DIR, exist_ok=True)
    works = all_works()
    unknown = set(SPLIT) - {w["work"] for w in works}
    assert not unknown, f"SPLIT names works that do not exist: {unknown}"

    pairs = {"train": [], "val": []}
    records = {"val": [], "test": []}
    manifest_works = []
    totals = Counter()
    for w in works:
        split = SPLIT.get(w["work"], "train")
        counts = Counter()
        for kind, text in units_of(w["text"]):
            words, gaps = strip.strip_line(text)
            if not words:
                counts["dropped_no_words"] += 1
                continue
            if not fits(words):
                counts["dropped_too_long"] += 1
                continue
            slots = strip.collapse(gaps)
            counts[kind] += 1
            counts["gaps"] += len(gaps)
            counts["gaps_marked"] += sum(1 for g in gaps if g)
            counts["gaps_multi"] += sum(1 for g in gaps if len(g) > 1)
            line = " ".join(words) + strip.SEP + strip.slot_string(words, slots)
            if split in pairs:
                pairs[split].append(line)
            if split in records:
                records[split].append({"work": w["work"], "ebook": w["ebook"], "kind": kind,
                                       "words": words, "slots": slots, "gaps": gaps})
        units = counts["verse"] + counts["prose"] + counts["other"]
        manifest_works.append({
            "work": w["work"], "title": w["title"], "author": w["author"], "split": split,
            "ebook": w["ebook"], "edition": EDITIONS[w["ebook"]],
            "chars": len(w["text"]), "units": units,
            "verse": counts["verse"], "prose": counts["prose"], "other": counts["other"],
            "dropped_too_long": counts["dropped_too_long"], "dropped_no_words": counts["dropped_no_words"],
        })
        for k, v in counts.items():
            totals[f"{split}_{k}"] += v
            totals[k] += v

    rng = random.Random(SEED)
    for split, lines in pairs.items():
        rng.shuffle(lines)  # a line's neighbours are strangers, in training as at test
        with open(os.path.join(CORPUS_DIR, f"{split}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    for split, recs in records.items():
        with open(os.path.join(CORPUS_DIR, f"{split}.jsonl"), "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    kept = totals["verse"] + totals["prose"] + totals["other"]
    too_long = totals["dropped_too_long"]
    sources = {}
    for eid in [xl.SHAKESPEARE_ID] + [e for e, _ in xl.CONTEMPORARIES]:
        raw = _raw(eid)
        updated = re.search(r"Most recently updated: (.+)", raw)
        sources[str(eid)] = {
            "url": f"https://www.gutenberg.org/ebooks/{eid}",
            "edition": EDITIONS[eid],
            "gutenberg_updated": updated.group(1).strip() if updated else None,
            "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        }
    by_split = {s: {"works": sum(1 for m in manifest_works if m["split"] == s),
                    "units": sum(m["units"] for m in manifest_works if m["split"] == s),
                    "chars": sum(m["chars"] for m in manifest_works if m["split"] == s)}
                for s in ("train", "val", "test")}
    manifest = {
        "about": "pointing split manifest: every work, the Gutenberg volume and edition its text "
                 "comes from, and the split it sits in. Held out by whole work.",
        "built_by": "projects/pointing/data/build_corpus.py",
        "source_list": "projects/shakespeare/data/_xl_corpus.py",
        "block_size": BLOCK_SIZE,
        "shuffle_seed": SEED,
        "splits": by_split,
        "units": {"kept": kept, "verse": totals["verse"], "prose": totals["prose"], "other": totals["other"],
                  "dropped_too_long": too_long, "dropped_too_long_share": round(too_long / (kept + too_long), 5),
                  "dropped_no_words": totals["dropped_no_words"]},
        "gaps": {"total": totals["gaps"], "marked": totals["gaps_marked"], "multi_mark": totals["gaps_multi"],
                 "multi_mark_share_of_marked": round(totals["gaps_multi"] / totals["gaps_marked"], 5)},
        "sources": sources,
        "works": manifest_works,
    }
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    for s, v in by_split.items():
        print(f"{s:<5} {v['works']:>3} works  {v['units']:>8,} units  {v['chars']:>10,} chars")
    print(f"units kept {kept:,} (verse {totals['verse']:,} / prose {totals['prose']:,} / other {totals['other']:,})")
    print(f"dropped: too long for block {BLOCK_SIZE}: {too_long:,} "
          f"({too_long / (kept + too_long):.3%}); no words: {totals['dropped_no_words']:,}")
    print(f"gaps: {totals['gaps']:,}, marked {totals['gaps_marked']:,}, "
          f"holding 2+ marks {totals['gaps_multi']:,} ({totals['gaps_multi'] / totals['gaps_marked']:.2%} of marked)")
    print(f"wrote {MANIFEST}")


if __name__ == "__main__":
    main()
