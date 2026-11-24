"""generate.py — the oblique corpus, written by named models through tools/synthgen.

Four OpenRouter models each write both registers: strategies (`s`, a short
instruction to a stuck artist that comes at the problem from the side) and
fortunes (`f`, a sincere one-line fortune). The prompts describe the shape
and show no examples, so nothing in them can be copied back.

One request asks for LINES lines. Each request carries two theme words drawn
from one list shared by both registers, so the registers differ in the move
they make and not in what they are about.

Every paid response is appended to data/ledger.jsonl the moment it returns
(gitignored; a crash loses nothing that was paid for). At the end of a run
the whole ledger is rewritten as the committed record:

    data/raw.txt         every response, concatenated (synthgen.write_corpus)
    data/manifest.json   synthgen's manifest: generators, per-response cost and
                         offsets into raw.txt, register and themes in `extra`
    data/costs.jsonl     one line per run

Run from the repo root (the key comes from the environment or .env.local):
    uv run python projects/oblique/data/generate.py --pilot
    uv run python projects/oblique/data/generate.py --requests 60 --budget 4.00
"""
import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "synthgen"))
import synthgen as sg  # noqa: E402

LEDGER = os.path.join(HERE, "ledger.jsonl")
RAW = os.path.join(HERE, "raw.txt")
MANIFEST = os.path.join(HERE, "manifest.json")
COSTS = os.path.join(HERE, "costs.jsonl")

# The studio names the models it pays for (ADR-0038). No default, no fallback.
MODELS = [
    "anthropic/claude-haiku-5.5",
    "openai/gpt-6-luna",
    "deepseek/deepseek-v4.1-flash",
    "meta/muse-ember",
]

LINES = 50
TEMPERATURE = 1.0
MAX_TOKENS = 1400
SEED = 1975

SHAPES = {
    "s": ("Each line is a short instruction to a stuck artist that approaches "
          "the problem from the side; never advice, never a platitude; under "
          "twelve words."),
    "f": ("Each line is a one-line fortune, sincere, second person, under "
          "twelve words, no proper nouns."),
}

PROMPT = """Write {n} original lines, one per line.

{shape}

Rules:
- One sentence per line, ending with a full stop, a question mark or an exclamation mark.
- No proper nouns, no numbers, no quotation marks.
- Every line is new. Do not quote or adapt any existing card deck, book, proverb or slogan.
- Vary the opening words and the rhythm from line to line.
- Let these two words colour some of the lines without appearing in most of them: {a}, {b}.

Output only the {n} lines. No numbering, no bullets, no commentary."""

# One list for both registers. Plain nouns, nothing register-specific.
THEMES = """door river clock kitchen ladder window thread salt mirror garden
bridge shadow engine letter coin stone rain map key candle road table pocket
bell seed rope wall chair bread mountain market harbour station attic fence
needle drum wheel lantern orchard hallway staircase roof cellar field shore
island tunnel tower basement corner edge surface border margin gap knot hinge
handle lid drawer shelf box envelope stamp ticket receipt list ledger calendar
morning evening midnight winter summer weather wind fog frost tide harvest
neighbour stranger guest child teacher rival friend crowd audience queue
voice silence echo rhythm colour paper ink dust ash smoke glass iron wood wool
water fire soil root branch leaf bird fish horse dog hand eye breath sleep
hunger appetite memory habit mistake accident rumour promise debt gift
errand journey detour shortcut delay return beginning ending middle half
weight speed distance height noise pattern outline draft copy fragment
remainder repair tool machine signal button switch wire battery lens frame""".split()


def plan(requests: int, start: int):
    """The (model, register, themes) grid for one run. `start` is how many
    requests each (model, register) pair already has in the ledger, so a
    top-up run continues the theme sequence instead of repeating it."""
    jobs = []
    for model in MODELS:
        for reg in ("s", "f"):
            # The theme sequence is seeded by position only, so the two
            # registers and all four models draw the same pairs in order.
            rng = random.Random(SEED)
            pairs = [tuple(rng.sample(THEMES, 2)) for _ in range(start + requests)]
            for i in range(start, start + requests):
                jobs.append((model, reg, i, pairs[i]))
    return jobs


def read_ledger():
    if not os.path.exists(LEDGER):
        return []
    with open(LEDGER, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def to_sample(rec: dict) -> sg.Sample:
    return sg.Sample(**rec)


def to_record(s: sg.Sample) -> dict:
    return {k: getattr(s, k) for k in s.__dataclass_fields__}


def write_record(run_id: str, new_samples, budget, backend, params):
    """Rewrite raw.txt + manifest.json from the whole ledger, and append this
    run's line to costs.jsonl."""
    samples = [to_sample(r) for r in read_ledger()]
    kept = [s for s in samples if s.text.strip()]
    dropped = [sg.Drop(i, s.model, "empty", None, None, "")
               for i, s in enumerate(samples) if not s.text.strip()]
    sg.write_corpus(kept, RAW)
    manifest = sg.build_manifest(
        samples, kept, dropped, prompt=PROMPT, params=params,
        backend=backend, corpus_path=RAW)
    # The manifest is cumulative over every run; the budget fields describe
    # the run that just finished.
    manifest["shapes"] = SHAPES
    manifest["runs"] = sorted({s.extra.get("run") for s in samples})
    manifest["budget_usd"] = budget.limit_usd
    manifest["budget_hit"] = bool(budget.hit)
    sg.write_manifest(manifest, MANIFEST)
    if new_samples:
        run_kept = [s for s in new_samples if s.text.strip()]
        run_manifest = sg.build_manifest(
            new_samples, run_kept, [], prompt=PROMPT, params=params,
            backend=backend, budget=budget)
        rec = sg.cost_record(run_manifest, os.path.relpath(RAW, ROOT))
        rec["run"] = run_id
        sg.append_cost_record(rec, COSTS)
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--requests", type=int, default=0,
                    help="new requests per (model, register) pair")
    ap.add_argument("--lines", type=int, default=LINES)
    ap.add_argument("--budget", type=float, required=False, default=None,
                    help="dollar ceiling for THIS run (required unless --rebuild)")
    ap.add_argument("--models", default=None,
                    help="comma-separated subset of the named four")
    ap.add_argument("--pilot", action="store_true",
                    help="one request of 30 lines per (model, register)")
    ap.add_argument("--effort", default="none",
                    help="reasoning effort; model=effort pairs override, e.g. "
                         "none,openai/gpt-6-luna=minimal")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--rebuild", action="store_true",
                    help="rewrite raw.txt + manifest.json from the ledger; no requests")
    args = ap.parse_args()

    backend = sg.get_backend("openrouter")
    efforts = {}
    default_effort = "none"
    for part in args.effort.split(","):
        if "=" in part:
            m, e = part.split("=", 1)
            efforts[m] = e
        elif part:
            default_effort = part
    params = {"temperature": TEMPERATURE, "max_tokens": MAX_TOKENS,
              "lines_per_request": args.lines, "reasoning_effort": default_effort,
              "reasoning_effort_overrides": efforts, "jaccard_threshold": None,
              "seed": SEED, "themes": len(THEMES)}

    if args.rebuild:
        m = write_record("rebuild", [], sg.Budget(), backend, params)
        print(f"rebuilt: {m['counts']['generated']} responses, ${m['total_cost_usd']:.4f}")
        return
    if args.budget is None:
        ap.error("--budget is required for a paid run")

    models = [m.strip() for m in args.models.split(",")] if args.models else MODELS
    unknown = [m for m in models if m not in MODELS]
    if unknown:
        ap.error(f"not one of the named models: {unknown}")

    ledger = read_ledger()
    spent_before = sum(r["cost_usd"] for r in ledger)
    done = {}
    for r in ledger:
        if r["extra"].get("pilot"):
            continue
        k = (r["model"], r["extra"]["register"])
        done[k] = max(done.get(k, 0), r["extra"]["index"] + 1)

    n_lines = 30 if args.pilot else args.lines
    run_id = time.strftime("%Y%m%dT%H%M%S") + ("-pilot" if args.pilot else "")
    if args.pilot:
        jobs = [(m, reg, 0, ("door", "river")) for m in models for reg in ("s", "f")]
    else:
        # continue each pair's theme sequence past what the ledger holds
        jobs = []
        for model in models:
            for reg in ("s", "f"):
                start = done.get((model, reg), 0)
                jobs += [j for j in plan(args.requests, start)
                         if j[0] == model and j[1] == reg]
    random.Random(SEED).shuffle(jobs)   # interleave models so a budget stop is even
    print(f"run {run_id}: {len(jobs)} requests x {n_lines} lines; "
          f"spent before ${spent_before:.4f}; this run's ceiling ${args.budget:.2f}")

    budget = sg.Budget(limit_usd=args.budget)
    new, failures = [], {}

    def one(job):
        model, reg, idx, (a, b) = job
        prompt = PROMPT.format(n=n_lines, shape=SHAPES[reg], a=a, b=b)
        out = sg.generate(model, prompt, n=1, temperature=TEMPERATURE,
                          max_tokens=MAX_TOKENS,
                          reasoning_effort=efforts.get(model, default_effort),
                          backend=backend, budget=budget, timeout=180)
        for s in out:
            s.extra = {"register": reg, "index": idx, "themes": [a, b],
                       "lines_requested": n_lines, "run": run_id,
                       **({"pilot": True} if args.pilot else {})}
        return out

    with ThreadPoolExecutor(max_workers=args.workers) as pool, \
            open(LEDGER, "a", encoding="utf-8") as ledger_f:
        futures = {pool.submit(one, j): j for j in jobs}
        for n, fut in enumerate(as_completed(futures), 1):
            job = futures[fut]
            try:
                out = fut.result()
            except sg.SynthGenError as e:
                failures.setdefault(job[0], []).append(str(e))
                continue
            for s in out:
                ledger_f.write(json.dumps(to_record(s), ensure_ascii=False) + "\n")
                ledger_f.flush()
                new.append(s)
            if n % 20 == 0:
                print(f"  {n}/{len(jobs)} done, ${budget.spent_usd:.4f} this run", flush=True)

    manifest = write_record(run_id, new, budget, backend, params)
    print(f"\nthis run: {len(new)} responses, ${budget.spent_usd:.4f}"
          f"{' (budget hit)' if budget.hit else ''}")
    by = {}
    for s in new:
        r = by.setdefault(s.model, {"n": 0, "cost": 0.0, "out": 0, "lines": 0, "empty": 0})
        r["n"] += 1
        r["cost"] += s.cost_usd
        r["out"] += s.completion_tokens
        r["lines"] += sum(1 for ln in s.text.split("\n") if ln.strip())
        r["empty"] += not s.text.strip()
    for m, r in sorted(by.items()):
        per = r["cost"] / r["lines"] * 1000 if r["lines"] else float("nan")
        print(f"  {m}: {r['n']} responses, {r['lines']} lines, {r['out']} completion "
              f"tokens, ${r['cost']:.4f} (${per:.4f} per 1k lines), {r['empty']} empty")
    for m, errs in failures.items():
        print(f"  !! {m}: {len(errs)} failed requests; first: {errs[0]}")
    print(f"cumulative: {manifest['counts']['generated']} responses, "
          f"${manifest['total_cost_usd']:.4f}")


if __name__ == "__main__":
    main()
