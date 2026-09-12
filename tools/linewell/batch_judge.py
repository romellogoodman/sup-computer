"""
Batch judging for linewell: many poems at once, verdicts by file or by local LLM.

compose.py plays one poem at a time with an interactive judge. This drives N
poems in parallel rounds so a judge that works in batches -- a frontier model
reading a file, or a local LLM behind steer -- can supply verdicts. Every
candidate is logged as one JSONL record with the poem-so-far, the line, its
NLL under the well, and the verdict: the training data for a learned judge.

Modes (all from the repo root):

    # start a batch of poems (starts x temperatures x replicates)
    uv run --with tokenizers python tools/linewell/batch_judge.py init \
        --state S.json --starts "  NURSE." "  ROMEO:" --temps 0.8 1.0 --reps 2

    # draw K candidates per unfinished poem; pending.txt hides the NLL so the
    # judge reads blind
    uv run --with tokenizers python tools/linewell/batch_judge.py draw \
        --state S.json --k 4 --pending pending.json

    # apply a verdict file {"<pid>.<cid>": true|false, ...}: log every
    # candidate, append the first accepted one to its poem
    uv run --with tokenizers python tools/linewell/batch_judge.py apply \
        --state S.json --pending pending.json --verdicts V.json \
        --log log.jsonl --judge claude-fable-5-1 --session 1

    # the local LLM judge runs draw+judge+apply in a loop until every poem
    # is done (or --rounds is exhausted)
    uv run --with tokenizers python tools/linewell/batch_judge.py llm \
        --state S.json --k 4 --log log.jsonl --rounds 16 --workers 4
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))

from compose import DEFAULT_MODEL_DIR, LLMJudge, LineWell  # noqa: E402

NEWLINE = "\n"


def load(path):
    with open(path) as f:
        return json.load(f)


def save(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def cmd_init(a):
    poems = []
    pid = 0
    for start in a.starts:
        for t in a.temps:
            for r in range(a.reps):
                poems.append({"id": pid, "start": start, "temperature": t, "rep": r,
                              "poem": [line for line in start.split(NEWLINE) if line],
                              "done": False, "round": 0})
                pid += 1
    save(a.state, {"lines": a.lines, "poems": poems})
    print(f"{len(poems)} poems -> {a.state}")


def draw(well, state, k, topk):
    pending = []
    for p in state["poems"]:
        if p["done"]:
            continue
        context = (NEWLINE.join(p["poem"]) + NEWLINE) if p["poem"] else NEWLINE
        seen = set()
        cid = 0
        tries = 0
        while cid < k and tries < k * 3:
            tries += 1
            line = well.sample_line(context, temperature=p["temperature"], topk=topk)
            if not line.strip() or line in seen:
                continue
            seen.add(line)
            nll = well.line_nll(context, line)
            pending.append({"pid": p["id"], "cid": cid, "context": list(p["poem"]),
                            "line": line, "nll": round(nll, 3), "round": p["round"]})
            cid += 1
    return pending


def write_blind(pending, path):
    """The judge-facing sheet: poem so far + candidates, no NLL."""
    with open(path, "w") as f:
        last = None
        for c in pending:
            if c["pid"] != last:
                last = c["pid"]
                f.write(f"\n### poem {c['pid']}\n")
                f.write((NEWLINE.join(c["context"]) if c["context"] else "(empty)") + NEWLINE)
                f.write("--- candidates\n")
            f.write(f"{c['pid']}.{c['cid']}: {c['line']}\n")


def cmd_draw(a):
    state = load(a.state)
    well = LineWell(a.model_dir, device=a.device)
    pending = draw(well, state, a.k, a.topk)
    save(a.pending, pending)
    write_blind(pending, a.pending.replace(".json", ".txt"))
    print(f"{len(pending)} candidates for {len({c['pid'] for c in pending})} poems -> {a.pending}")


def apply(state, pending, verdicts, log_path, judge, session):
    by_pid = {p["id"]: p for p in state["poems"]}
    appended = set()
    n = 0
    with open(log_path, "a") as log:
        for c in pending:
            key = f"{c['pid']}.{c['cid']}"
            if key not in verdicts:
                continue
            accepted = bool(verdicts[key])
            p = by_pid[c["pid"]]
            rec = {"session": session, "judge": judge, "pid": c["pid"], "start": p["start"],
                   "temperature": p["temperature"], "round": c["round"], "context": c["context"],
                   "line": c["line"], "nll": c["nll"], "accepted": accepted}
            log.write(json.dumps(rec, ensure_ascii=False) + NEWLINE)
            n += 1
            if accepted and c["pid"] not in appended:
                appended.add(c["pid"])
                p["poem"].append(c["line"])
                if len(p["poem"]) >= state["lines"]:
                    p["done"] = True
    for p in state["poems"]:
        if not p["done"]:
            p["round"] += 1
    return n, len(appended)


def cmd_apply(a):
    state = load(a.state)
    pending = load(a.pending)
    verdicts = load(a.verdicts)
    n, kept = apply(state, pending, verdicts, a.log, a.judge, a.session)
    save(a.state, state)
    done = sum(p["done"] for p in state["poems"])
    print(f"logged {n} verdicts, {kept} lines appended, {done}/{len(state['poems'])} poems done")


def cmd_llm(a):
    state = load(a.state)
    well = LineWell(a.model_dir, device=a.device)
    judge = LLMJudge(a.llm_model)
    for r in range(a.rounds):
        pending = draw(well, state, a.k, a.topk)
        if not pending:
            break
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            results = list(ex.map(lambda c: judge(c["context"], c["line"], c["nll"])[0], pending))
        verdicts = {f"{c['pid']}.{c['cid']}": ok for c, ok in zip(pending, results)}
        n, kept = apply(state, pending, verdicts, a.log, a.llm_model, a.session)
        save(a.state, state)
        done = sum(p["done"] for p in state["poems"])
        print(f"round {r}: {n} verdicts, {sum(results)} accepted, {kept} appended, "
              f"{done}/{len(state['poems'])} done", flush=True)
        if done == len(state["poems"]):
            break


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--state", required=True)
    common.add_argument("--model_dir", default=DEFAULT_MODEL_DIR)
    common.add_argument("--device", default="mps")
    common.add_argument("--topk", type=int, default=40)

    s = sub.add_parser("init", parents=[common])
    s.add_argument("--starts", nargs="+", required=True)
    s.add_argument("--temps", nargs="+", type=float, default=[0.9])
    s.add_argument("--reps", type=int, default=1)
    s.add_argument("--lines", type=int, default=8)

    s = sub.add_parser("draw", parents=[common])
    s.add_argument("--k", type=int, default=4)
    s.add_argument("--pending", required=True)

    s = sub.add_parser("apply", parents=[common])
    s.add_argument("--pending", required=True)
    s.add_argument("--verdicts", required=True)
    s.add_argument("--log", required=True)
    s.add_argument("--judge", required=True)
    s.add_argument("--session", type=int, default=1)

    s = sub.add_parser("llm", parents=[common])
    s.add_argument("--k", type=int, default=4)
    s.add_argument("--log", required=True)
    s.add_argument("--rounds", type=int, default=16)
    s.add_argument("--workers", type=int, default=4)
    s.add_argument("--llm_model", default="olmo-3-7b-instruct")
    s.add_argument("--session", type=int, default=1)

    a = ap.parse_args()
    {"init": cmd_init, "draw": cmd_draw, "apply": cmd_apply, "llm": cmd_llm}[a.cmd](a)


if __name__ == "__main__":
    main()
