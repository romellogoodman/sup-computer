"""harness.py -- the pointing eval: what the loss can't measure.

The corpus scores the model. For every line of the held-out works the harness
feeds the stripped words, takes the slot string greedily (temperature 0; this
is a labelling task), and diffs it slot by slot against the marks the edition
printed. No oracle and no judge.

What it reports, in the order a reader should trust it:

  well-formedness   output-length errors (the slot string is not 2n + 1 long)
                    and anchor errors (an anchor is not its word's first
                    letter). A line with either is malformed.
  mark scores       precision / recall / F1 per mark, over the slots of the
                    well-formed lines only, with the count stated
  line ends         the final gap, scored apart for verse, prose and other
  per source        the same scores split by Gutenberg volume (the edition), and
                    again within each kind of line, because volumes differ in
                    their mix of verse, prose and speaker labels
  exact match       the whole slot string right, over ALL lines (a malformed
                    line is a miss); also on the lines whose words never
                    appear as a training line
  no-mark accuracy  lines that need nothing and got nothing
  ceiling           gaps that held two or more marks keep only the first, so
                    the marks lost to that rule are counted per mark
  question distance recall of `?` by how many words back its question word is
  baseline          "no marks, then the commonest final mark" on the same lines

Modes:
    --out_dir RUN                 score RUN/ckpt.pt on the test works
    --out_dir RUN --curve         score every RUN/ckpt-*.pt on a fixed 4,000-line
                                  sample of the test works (per-mark F1 by iter).
                                  Each scored snapshot is cached beside its
                                  checkpoint; --snapshot PATH scores just one.
    --out_dir RUN --modern        score the twenty hand-typed modern lines
    --split val                   use the val works instead

Frozen release copy. Run in place (after training); results land in results/:
    python harness.py
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import pickle
import random
import sys
from collections import Counter, defaultdict

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import strip  # noqa: E402
from checkpoint import load_model  # noqa: E402  (vendored: no cross-folder imports)

CORPUS = os.path.join(HERE, "corpus")
META = os.path.join(HERE, "tokenized", "meta.pkl")
MODERN = os.path.join(HERE, "modern_sample.txt")
CURVE_LINES = 4000
OVERRUN = 6  # slots a line may run past 2n + 1 before generation gives up on it

# P2's question words. A wh-word counts anywhere in the clause; an auxiliary
# counts only as the clause's first word, where it inverts.
WH = {"who", "whom", "whose", "what", "which", "when", "where", "wherefore", "why", "how",
      "whence", "whither"}
AUX = {"is", "are", "art", "am", "was", "were", "wert", "do", "dost", "doth", "does", "did",
       "didst", "have", "hast", "hath", "had", "shall", "shalt", "will", "wilt", "would",
       "wouldst", "should", "shouldst", "can", "canst", "could", "couldst", "may", "mayst",
       "might", "must", "dare"}
DIST_BINS = [(1, 2), (3, 5), (6, 9), (10, 999)]


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [center - half, center + half]


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": p, "recall": r, "f1": f, "gold": tp + fn, "predicted": tp + fp}


@torch.no_grad()
def point(model, meta, device, lines, batch_size=256):
    """Greedy slot strings for a list of word lists. Lines are batched by the
    exact length of their prompt, so nothing is ever padded."""
    stoi, itos = meta["stoi"], meta["itos"]
    nl = stoi["\n"]
    block = model.config.block_size
    buckets = defaultdict(list)
    for i, words in enumerate(lines):
        buckets[len(" ".join(words))].append(i)
    out = [""] * len(lines)
    for _, idxs in sorted(buckets.items()):
        for b in range(0, len(idxs), batch_size):
            chunk = idxs[b:b + batch_size]
            prompts = ["\n" + " ".join(lines[i]) + strip.SEP for i in chunk]
            x = torch.tensor([[stoi[c] for c in p] for p in prompts], dtype=torch.long, device=device)
            start = x.size(1)
            cap = [2 * len(lines[i]) + 1 + OVERRUN for i in chunk]
            done = [False] * len(chunk)
            for step in range(max(cap)):
                if x.size(1) >= block:
                    break
                logits, _ = model(x)
                nxt = logits[:, -1, :].argmax(-1)
                x = torch.cat([x, nxt[:, None]], dim=1)
                for j, t in enumerate(nxt.tolist()):
                    if t == nl or step + 1 >= cap[j]:
                        done[j] = True
                if all(done):
                    break
            for j, i in enumerate(chunk):
                ids = x[j, start:].tolist()
                if nl in ids:
                    ids = ids[:ids.index(nl)]
                out[i] = "".join(itos[t] for t in ids[:cap[j]])
    return out


def gold_string(rec) -> str:
    return strip.slot_string(rec["words"], rec["slots"])


def check(rec, pred: str):
    """-> (length_ok, anchors_ok, predicted slots or None)."""
    words = rec["words"]
    length_ok = len(pred) == 2 * len(words) + 1
    anchors_ok = all(pred[2 * i + 1] == w[0] for i, w in enumerate(words) if 2 * i + 1 < len(pred))
    slots = [pred[2 * i] for i in range(len(words) + 1)] if length_ok and anchors_ok else None
    return length_ok, anchors_ok, slots


def question_distance(words, slots, gap: int):
    """Words from the clause's question word to the `?` in `gap`, or None."""
    start = 0
    for g in range(gap - 1, 0, -1):
        if slots[g] in strip.TERMINALS:
            start = g
            break
    for i in range(start, gap):
        if words[i] in WH or (i == start and words[i] in AUX):
            return gap - i
    return None


def score(recs, preds, train_inputs=None) -> dict:
    n = len(recs)
    length_err = anchor_err = exact = 0
    short = long_ = 0
    slot_tp, slot_fp, slot_fn = Counter(), Counter(), Counter()
    slots_total = slots_right = 0
    end = defaultdict(lambda: {"n": 0, "right": 0, "gold": Counter(), "pred": Counter(), "tp": Counter(),
                               "confusion": Counter()})
    by_src = defaultdict(lambda: {"n": 0, "exact": 0, "malformed": 0, "tp": Counter(), "fp": Counter(),
                                  "fn": Counter(), "slots": 0, "slots_right": 0})
    by_kind = defaultdict(lambda: {"n": 0, "exact": 0})
    nomark = {"n": 0, "right": 0}
    unseen = {"n": 0, "exact": 0}
    qdist = defaultdict(lambda: [0, 0])
    lost = Counter()
    kept = Counter()
    multi_gaps = marked_gaps = 0
    examples = []

    for rec, pred in zip(recs, preds):
        words, gold = rec["words"], rec["slots"]
        kind, src = rec.get("kind", "other"), str(rec.get("ebook", "modern"))
        length_ok, anchors_ok, slots = check(rec, pred)
        is_exact = pred == gold_string(rec)
        exact += is_exact
        length_err += not length_ok
        anchor_err += not anchors_ok
        if not length_ok:
            if len(pred) < 2 * len(words) + 1:
                short += 1
            else:
                long_ += 1
        by_kind[kind]["n"] += 1
        by_kind[kind]["exact"] += is_exact
        s = by_src[src]
        s["n"] += 1
        s["exact"] += is_exact
        if train_inputs is not None and " ".join(words) not in train_inputs:
            unseen["n"] += 1
            unseen["exact"] += is_exact
        if all(g == strip.NONE for g in gold):
            nomark["n"] += 1
            nomark["right"] += is_exact
        for g in rec.get("gaps", []):
            if g:
                marked_gaps += 1
                kept[g[0]] += 1
                if len(g) > 1:
                    multi_gaps += 1
                    for m in g[1:]:
                        lost[m] += 1
        if slots is None:
            s["malformed"] += 1
            if len(examples) < 40:
                examples.append({"words": " ".join(words), "gold": gold_string(rec), "pred": pred,
                                 "problem": "length" if not length_ok else "anchor"})
            continue
        for gi, (g, p) in enumerate(zip(gold, slots)):
            slots_total += 1
            s["slots"] += 1
            if g == p:
                slots_right += 1
                s["slots_right"] += 1
                if g != strip.NONE:
                    slot_tp[g] += 1
                    s["tp"][g] += 1
            else:
                if g != strip.NONE:
                    slot_fn[g] += 1
                    s["fn"][g] += 1
                if p != strip.NONE:
                    slot_fp[p] += 1
                    s["fp"][p] += 1
            if g == "?":
                d = question_distance(words, gold, gi)
                key = "no question word" if d is None else next(f"{a}-{b}" if b < 999 else f"{a}+"
                                                                 for a, b in DIST_BINS if a <= d <= b)
                qdist[key][0] += p == "?"
                qdist[key][1] += 1
        e = end[kind]
        g, p = gold[-1], slots[-1]
        e["n"] += 1
        e["right"] += g == p
        e["gold"][g] += 1
        e["pred"][p] += 1
        e["tp"][g] += g == p
        e["confusion"][f"{g}>{p}"] += 1
        if not is_exact and len(examples) < 40 and len(words) > 3:
            examples.append({"words": " ".join(words), "gold": gold_string(rec), "pred": pred, "problem": "marks"})

    wellformed = sum(e["n"] for e in end.values())
    per_mark = {strip.MARK_NAMES[m]: {"mark": m, **prf(slot_tp[m], slot_fp[m], slot_fn[m])} for m in strip.MARKS}
    tp, fp, fn = sum(slot_tp.values()), sum(slot_fp.values()), sum(slot_fn.values())
    line_end = {}
    for kind, e in end.items():
        marks = {}
        for m in [".", ",", "?", "!", ";", ":", strip.NONE]:
            t = e["tp"][m]
            marks[m] = {**prf(t, e["pred"][m] - t, e["gold"][m] - t), "share_of_gold": e["gold"][m] / e["n"] if e["n"] else 0.0}
        line_end[kind] = {"lines": e["n"], "accuracy": e["right"] / e["n"] if e["n"] else 0.0, "marks": marks,
                          "confusion_top": dict(e["confusion"].most_common(16))}
    per_source = {}
    for src, s in by_src.items():
        stp, sfp, sfn = sum(s["tp"].values()), sum(s["fp"].values()), sum(s["fn"].values())
        per_source[src] = {
            "lines": s["n"], "exact_match": s["exact"] / s["n"], "malformed": s["malformed"] / s["n"],
            "slot_accuracy": s["slots_right"] / s["slots"] if s["slots"] else 0.0,
            "all_marks": prf(stp, sfp, sfn),
            "marks": {strip.MARK_NAMES[m]: prf(s["tp"][m], s["fp"][m], s["fn"][m]) for m in [",", ".", ";", ":", "?", "!"]},
        }
    return {
        "lines": n,
        "wellformedness": {
            "length_errors": length_err, "length_error_rate": length_err / n, "too_short": short, "too_long": long_,
            "anchor_errors": anchor_err, "anchor_error_rate": anchor_err / n,
            "wellformed_lines": wellformed, "wellformed_rate": wellformed / n,
        },
        "exact_match": {"rate": exact / n, "wilson_95": wilson(exact, n), "exact": exact,
                        "by_kind": {k: {"lines": v["n"], "rate": v["exact"] / v["n"]} for k, v in by_kind.items()},
                        "unseen_input": {"lines": unseen["n"], "rate": unseen["exact"] / unseen["n"] if unseen["n"] else None}},
        "no_mark": {"lines": nomark["n"], "accuracy": nomark["right"] / nomark["n"] if nomark["n"] else None},
        "slots": {"scored": slots_total, "accuracy": slots_right / slots_total if slots_total else 0.0,
                  "all_marks": prf(tp, fp, fn)},
        "per_mark": per_mark,
        "line_end": line_end,
        "per_source": per_source,
        "question_distance": {k: {"recall": a / b if b else None, "hits": a, "gold": b, "wilson_95": wilson(a, b)}
                              for k, (a, b) in qdist.items()},
        "ceiling": {"marked_gaps": marked_gaps, "gaps_with_two_or_more_marks": multi_gaps,
                    "share": multi_gaps / marked_gaps if marked_gaps else 0.0,
                    "marks_lost_to_collapse": {strip.MARK_NAMES[m]: {"lost": lost[m], "kept": kept[m],
                                                                    "recall_ceiling": kept[m] / (kept[m] + lost[m]) if kept[m] + lost[m] else None}
                                               for m in strip.MARKS}},
        "examples": examples,
    }


def baseline_preds(recs, train_path):
    """No marks anywhere, then the commonest final mark in training."""
    final = Counter()
    with open(train_path, encoding="utf-8") as f:
        for line in f:
            final[line.rstrip("\n")[-1]] += 1
    m = final.most_common(1)[0][0]
    return [strip.slot_string(r["words"], [strip.NONE] * len(r["words"]) + [m]) for r in recs], m


def load_recs(split):
    with open(os.path.join(CORPUS, f"{split}.jsonl"), encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def modern_recs():
    recs = []
    with open(MODERN, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            words, gaps = strip.strip_line(line)
            recs.append({"work": "modern", "ebook": "modern", "kind": "prose", "text": line,
                         "words": words, "slots": strip.collapse(gaps), "gaps": gaps})
    return recs


def headline(tag, r):
    w = r["wellformedness"]
    print(f"[{tag}] lines {r['lines']:,}; length errors {w['length_error_rate']:.2%}, anchor errors {w['anchor_error_rate']:.2%}")
    print(f"[{tag}] exact match {r['exact_match']['rate']:.1%}; no-mark accuracy "
          f"{r['no_mark']['accuracy'] if r['no_mark']['accuracy'] is None else format(r['no_mark']['accuracy'], '.1%')}; "
          f"slot accuracy {r['slots']['accuracy']:.1%}")
    for name in ["period", "comma", "question", "exclamation", "colon", "semicolon"]:
        m = r["per_mark"][name]
        print(f"[{tag}]   {name:<12} P {m['precision']:.1%}  R {m['recall']:.1%}  F1 {m['f1']:.1%}  (gold {m['gold']:,})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", default=HERE)
    ap.add_argument("--split", default="test", choices=["test", "val"])
    ap.add_argument("--curve", action="store_true")
    ap.add_argument("--snapshot", default=None, help="with --curve: score this one ckpt-*.pt into its cache and stop")
    ap.add_argument("--modern", action="store_true")
    ap.add_argument("--rescore", action="store_true", help="score the slot strings saved by the last full run")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--device", default=None)
    args = ap.parse_args()
    tag = args.tag or os.path.basename(os.path.normpath(args.out_dir))
    with open(META, "rb") as f:
        meta = pickle.load(f)
    research = os.path.join(HERE, "results")
    os.makedirs(research, exist_ok=True)

    if args.curve:
        recs = load_recs(args.split)
        recs = random.Random(1337).sample(recs, min(CURVE_LINES, len(recs)))
        lines = [r["words"] for r in recs]
        points = []
        for path in [args.snapshot] if args.snapshot else sorted(glob.glob(os.path.join(args.out_dir, "ckpt-*.pt"))):
            # a scored snapshot is kept beside it, so the curve can be built up
            # while the run is still training
            cached = path[:-3] + f".curve-{args.split}.json"
            if os.path.exists(cached):
                with open(cached, encoding="utf-8") as f:
                    points.append(json.load(f))
                continue
            model, ckpt = load_model(path, args.device)
            r = score(recs, point(model, meta, next(model.parameters()).device, lines))
            points.append({
                "iter": ckpt["iter_num"],
                "exact_match": r["exact_match"]["rate"],
                "length_error_rate": r["wellformedness"]["length_error_rate"],
                "anchor_error_rate": r["wellformedness"]["anchor_error_rate"],
                "all_marks_f1": r["slots"]["all_marks"]["f1"],
                "f1": {k: v["f1"] for k, v in r["per_mark"].items()},
                "recall": {k: v["recall"] for k, v in r["per_mark"].items()},
                "precision": {k: v["precision"] for k, v in r["per_mark"].items()},
            })
            with open(cached, "w", encoding="utf-8") as f:
                json.dump(points[-1], f)
            print(f"[{tag}] iter {ckpt['iter_num']:>5}: exact {r['exact_match']['rate']:.1%}  "
                  + "  ".join(f"{k[:5]} {points[-1]['f1'][k]:.2f}" for k in ["period", "comma", "question", "colon", "semicolon"]))
        if args.snapshot:
            return
        gold = Counter(s for r in recs for s in r["slots"] if s != strip.NONE)
        out = {"tag": tag, "split": args.split, "lines": len(recs), "sample_seed": 1337,
               "gold_in_sample": {strip.MARK_NAMES[m]: gold[m] for m in strip.MARKS}, "points": points}
        path = os.path.join(research, f"curve-{tag}.json")
    else:
        model, ckpt = load_model(args.out_dir, args.device)
        device = next(model.parameters()).device
        if args.modern:
            recs = modern_recs()
            preds = point(model, meta, device, [r["words"] for r in recs])
            r = score(recs, preds)
            r["lines_detail"] = [{"text": rec["text"], "words": " ".join(rec["words"]), "gold": gold_string(rec), "pred": p,
                                  "rendered": strip.render(rec["words"], check(rec, p)[2]) if check(rec, p)[2] else None}
                                 for rec, p in zip(recs, preds)]
            path = os.path.join(research, f"modern-{tag}.json")
        else:
            recs = load_recs(args.split)
            if args.limit:
                recs = random.Random(1337).sample(recs, args.limit)
            train_path = os.path.join(CORPUS, "train.txt")
            with open(train_path, encoding="utf-8") as f:
                train_inputs = {line.split(strip.SEP)[0] for line in f}
            # the slot strings are kept in the run folder, so a new breakdown
            # can be scored later without generating again (--rescore)
            preds_path = os.path.join(args.out_dir, f"preds-{args.split}.json")
            if args.rescore and not args.limit:
                with open(preds_path, encoding="utf-8") as f:
                    preds = json.load(f)
                assert len(preds) == len(recs)
            else:
                preds = point(model, meta, device, [x["words"] for x in recs])
                if not args.limit:
                    with open(preds_path, "w", encoding="utf-8") as f:
                        json.dump(preds, f, ensure_ascii=False)
            r = score(recs, preds, train_inputs)
            base, m = baseline_preds(recs, train_path)
            b = score(recs, base, train_inputs)
            # a source's line mix differs (one volume is a third speaker labels,
            # another almost none), so sources are also compared kind by kind
            cells = defaultdict(list)
            for i, rec in enumerate(recs):
                cells[(str(rec["ebook"]), rec["kind"])].append(i)
            r["per_source_by_kind"] = {}
            for (src, kind), idx in sorted(cells.items()):
                sub = score([recs[i] for i in idx], [preds[i] for i in idx])
                sub_b = score([recs[i] for i in idx], [base[i] for i in idx])
                r["per_source_by_kind"].setdefault(src, {})[kind] = {
                    "lines": len(idx), "exact_match": sub["exact_match"]["rate"],
                    "baseline_exact_match": sub_b["exact_match"]["rate"],
                    "slot_accuracy": sub["slots"]["accuracy"], "all_marks_f1": sub["slots"]["all_marks"]["f1"],
                    "comma_f1": sub["per_mark"]["comma"]["f1"], "period_f1": sub["per_mark"]["period"]["f1"],
                    "final_slot_accuracy": sub["line_end"][kind]["accuracy"] if kind in sub["line_end"] else None,
                }
            r["baseline"] = {"rule": f"no marks, then a final {m!r}", "exact_match": b["exact_match"]["rate"],
                             "slot_accuracy": b["slots"]["accuracy"], "all_marks": b["slots"]["all_marks"],
                             "by_kind": b["exact_match"]["by_kind"]}
            suffix = "" if args.split == "test" and not args.limit else f"-{args.split}" + (f"-{args.limit}" if args.limit else "")
            path = os.path.join(research, f"eval-{tag}{suffix}.json")
        headline(tag, r)
        out = {"tag": tag, "run_dir": args.out_dir, "split": "modern" if args.modern else args.split,
               "protocol": {"temperature": 0, "decode": "greedy", "prompt": "newline + words + separator"},
               "iter": ckpt["iter_num"], "best_val_loss": float(ckpt["best_val_loss"]),
               "params": sum(p.numel() for p in model.parameters()), **r}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
