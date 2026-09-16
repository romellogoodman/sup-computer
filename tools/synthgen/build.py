#!/usr/bin/env python3
"""synthgen CLI — discover -> generate (mixture of models) -> dedup -> write.

Ties the engine together end to end and writes a project-ready ``raw.txt`` plus
its provenance ``manifest.json`` and one ``costs.jsonl`` line. Like
``tools/dataviz/build.py``, this is the operator entry point; the reusable
engine is ``synthgen.py``.

Examples
--------
    python build.py --list                       # what chat models are loaded?

    # demo: 4 samples from every loaded model, dedup, write to ./output/
    python build.py --n 4 --prompt "Write a 3-sentence bedtime story."

    # mixture-of-models into a project's data dir (drop-in for prepare.py)
    python build.py --n 50 \
        --models qwen/qwen3.6-27b,granite-4.1-8b,olmo-3-7b-instruct \
        --prompt-file prompt.txt \
        --out ../../projects/gatsby/data

    # the paid backend: models are always named, cost is capped (ADR-0038)
    python build.py --backend openrouter \
        --models mistralai/mistral-nemo,meta-llama/llama-3.1-8b-instruct \
        --n 50 --budget 2.00 --prompt-file prompt.txt --out ../../projects/x/data

The default backend is LM Studio's server at http://localhost:1234/v1
(override with SYNTHGEN_BASE_URL). OpenRouter reads OPENROUTER_API_KEY from
the environment, else the repo-root .env.local, else .env. Nothing is
generated until you run this.
"""
import argparse
import os
import sys

import synthgen as sg

# A self-contained demo prompt so `build.py` runs with no extra files.
DEMO_PROMPT = "Write a very short, simple story (3-4 sentences) for young children."


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", default="lmstudio", choices=sg.BACKENDS,
                    help="lmstudio (default, local, free) or openrouter (hosted, "
                         "paid; needs OPENROUTER_API_KEY and --models)")
    ap.add_argument("--list", action="store_true",
                    help="discover and print the loaded chat models, then exit "
                         "(LM Studio only)")
    ap.add_argument("--models", default=None,
                    help="comma-separated model ids (LM Studio default: every "
                         "discovered chat model — the mixture-of-models path; "
                         "REQUIRED on openrouter)")
    ap.add_argument("--n", type=int, default=4, help="samples per model")
    ap.add_argument("--prompt", default=None, help="the generation prompt")
    ap.add_argument("--prompt-file", default=None, dest="prompt_file",
                    help="read the prompt from a file instead of --prompt")
    ap.add_argument("--system", default=None, help="optional system prompt")
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--max-tokens", type=int, default=512, dest="max_tokens")
    ap.add_argument("--reasoning-effort", default=sg.REASONING_EFFORT,
                    dest="reasoning_effort",
                    help='thinking-trace effort; "none" suppresses it (default). '
                         'Sent as reasoning_effort on LM Studio, reasoning.effort '
                         'on OpenRouter')
    ap.add_argument("--budget", type=float, default=None,
                    help="dollar ceiling for the run; generation stops cleanly "
                         "once the cumulative cost would pass it")
    ap.add_argument("--jaccard", type=float, default=0.85,
                    help="near-duplicate token-set Jaccard threshold")
    ap.add_argument("--out", default="output",
                    help="target dir for raw.txt + manifest.json + costs.jsonl "
                         "(e.g. a project's data/). Default: ./output (gitignored).")
    ap.add_argument("--corpus-name", default="raw.txt", dest="corpus_name")
    ap.add_argument("--manifest-name", default="manifest.json", dest="manifest_name")
    ap.add_argument("--cost-log-name", default="costs.jsonl", dest="cost_log_name")
    ap.add_argument("--base", default=None,
                    help="override the backend's base URL (LM Studio default: "
                         f"{sg.BASE}; OpenRouter: {sg.OPENROUTER_BASE})")
    args = ap.parse_args()

    # resolve the backend first: a missing key fails here, before any request
    try:
        backend = sg.get_backend(args.backend, base=args.base)
    except sg.SynthGenError as e:
        sys.exit(str(e))

    if args.list:
        try:
            models = sg.discover(backend=backend)
        except sg.SynthGenError as e:
            sys.exit(str(e))
        print(f"{len(models)} chat model(s) loaded in LM Studio:")
        for m in models:
            print(f"  - {m}")
        return

    # resolve prompt
    prompt = args.prompt
    if args.prompt_file:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read().strip()
    if not prompt:
        prompt = DEMO_PROMPT
        print("(no --prompt given; using the demo prompt)\n")

    # resolve model mix — explicit on OpenRouter, discovered on LM Studio
    if args.models:
        models = [m.strip() for m in args.models.split(",") if m.strip()]
    elif backend.discoverable:
        models = sg.discover(backend=backend)
    else:
        sys.exit(f"--models is required on {backend.name}: name every model "
                 "(e.g. --models mistralai/mistral-nemo,meta-llama/llama-3.1-8b-instruct).")
    if not models:
        sys.exit("no chat models available — load one in LM Studio first.")
    budget = sg.Budget(limit_usd=args.budget)
    print(f"backend: {backend.name} ({backend.base})")
    print(f"model mix ({len(models)}): {', '.join(models)}")
    print(f"generating {args.n} sample(s) per model "
          f"(temp={args.temperature}, max_tokens={args.max_tokens}, "
          f"{backend.reasoning_field}={args.reasoning_effort}"
          f"{f', budget=${args.budget:.6f}' if args.budget is not None else ''})...\n")

    # generate across the mix
    samples = []
    for model in models:
        if not budget.allows():
            print(f"  {model} ... skipped (budget hit)")
            continue
        print(f"  {model} ...", end=" ", flush=True)
        try:
            got = sg.generate(
                model, prompt, n=args.n, temperature=args.temperature,
                max_tokens=args.max_tokens, system=args.system,
                reasoning_effort=args.reasoning_effort, backend=backend,
                budget=budget,
            )
        except sg.SynthGenError as e:
            sys.exit(f"\n{e}")
        empties = sum(1 for s in got if not s.text.strip())
        out_tok = sum(s.completion_tokens for s in got)
        cost = sum(s.cost_usd for s in got)
        note = f"  (WARNING: {empties} empty — check reasoning_effort)" if empties else ""
        short = "  (stopped: budget hit)" if budget.hit and len(got) < args.n else ""
        print(f"{len(got)} sample(s), {out_tok} out tok, ${cost:.6f}{note}{short}")
        samples.extend(got)
    if budget.hit:
        print(f"\nbudget hit: ${budget.spent_usd:.6f} of ${budget.limit_usd:.6f} "
              f"spent after {budget.samples} sample(s)")

    # dedup (never silent)
    kept, dropped = sg.dedup(samples, jaccard_threshold=args.jaccard)
    print(f"\ndedup: kept {len(kept)}/{len(samples)}, dropped {len(dropped)}")
    for d in dropped:
        matched = f" ~ #{d.matched_index}" if d.matched_index is not None else ""
        sim = f" (jaccard {d.similarity})" if d.similarity is not None else ""
        print(f"  - dropped #{d.index} [{d.model}] {d.reason}{matched}{sim}: {d.preview}")

    if not kept:
        sys.exit("\nnothing kept after dedup — no corpus written.")

    # write raw.txt + manifest.json + a costs.jsonl line
    params = {
        "n_per_model": args.n,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "reasoning_effort": args.reasoning_effort,
        "system": args.system,
        "jaccard_threshold": args.jaccard,
    }
    corpus_path = os.path.join(args.out, args.corpus_name)
    manifest_path = os.path.join(args.out, args.manifest_name)
    cost_log_path = os.path.join(args.out, args.cost_log_name)
    sg.write_corpus(kept, corpus_path)
    manifest = sg.build_manifest(samples, kept, dropped, prompt=prompt,
                                 params=params, backend=backend,
                                 corpus_path=corpus_path, budget=budget)
    sg.write_manifest(manifest, manifest_path)
    sg.append_cost_record(sg.cost_record(manifest, corpus_path), cost_log_path)

    chars = manifest["counts"]["corpus_chars"]
    print(f"\nwrote {len(kept)} docs ({chars:,} chars) -> {corpus_path}")
    print(f"wrote provenance manifest        -> {manifest_path}")
    print(f"cost: ${manifest['total_cost_usd']:.6f}"
          f"{' (budget hit)' if manifest['budget_hit'] else ''}  -> {cost_log_path}")
    print("\nnext: cd <project> && python prepare.py   # raw.txt is a drop-in")


if __name__ == "__main__":
    main()
