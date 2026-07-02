#!/usr/bin/env python3
"""synthgen CLI — discover -> generate (mixture of models) -> dedup -> write.

Ties the engine together end to end and writes a project-ready ``raw.txt`` plus
its provenance ``manifest.json``. Like ``tools/dataviz/build.py``, this is the
operator entry point; the reusable engine is ``synthgen.py``.

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

Requires LM Studio's server running at http://localhost:1234/v1 (override with
SYNTHGEN_BASE_URL). Nothing is generated until you run this.
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
    ap.add_argument("--list", action="store_true",
                    help="discover and print the loaded chat models, then exit")
    ap.add_argument("--models", default=None,
                    help="comma-separated model ids (default: every discovered "
                         "chat model — the mixture-of-models path)")
    ap.add_argument("--n", type=int, default=4, help="samples per model")
    ap.add_argument("--prompt", default=None, help="the generation prompt")
    ap.add_argument("--prompt-file", default=None, dest="prompt_file",
                    help="read the prompt from a file instead of --prompt")
    ap.add_argument("--system", default=None, help="optional system prompt")
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--max-tokens", type=int, default=512, dest="max_tokens")
    ap.add_argument("--reasoning-effort", default=sg.REASONING_EFFORT,
                    dest="reasoning_effort",
                    help='thinking-trace effort; "none" suppresses it (default)')
    ap.add_argument("--jaccard", type=float, default=0.85,
                    help="near-duplicate token-set Jaccard threshold")
    ap.add_argument("--out", default="output",
                    help="target dir for raw.txt + manifest.json (e.g. a "
                         "project's data/). Default: ./output (gitignored).")
    ap.add_argument("--corpus-name", default="raw.txt", dest="corpus_name")
    ap.add_argument("--manifest-name", default="manifest.json", dest="manifest_name")
    ap.add_argument("--base", default=sg.BASE, help="LM Studio base URL")
    args = ap.parse_args()

    if args.list:
        models = sg.discover(base=args.base)
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

    # resolve model mix
    if args.models:
        models = [m.strip() for m in args.models.split(",") if m.strip()]
    else:
        models = sg.discover(base=args.base)
    if not models:
        sys.exit("no chat models available — load one in LM Studio first.")
    print(f"model mix ({len(models)}): {', '.join(models)}")
    print(f"generating {args.n} sample(s) per model "
          f"(temp={args.temperature}, max_tokens={args.max_tokens}, "
          f"reasoning_effort={args.reasoning_effort})...\n")

    # generate across the mix
    samples = []
    for model in models:
        print(f"  {model} ...", end=" ", flush=True)
        got = sg.generate(
            model, prompt, n=args.n, temperature=args.temperature,
            max_tokens=args.max_tokens, system=args.system,
            reasoning_effort=args.reasoning_effort, base=args.base,
        )
        empties = sum(1 for s in got if not s.text.strip())
        out_tok = sum(s.completion_tokens for s in got)
        note = f"  (WARNING: {empties} empty — check reasoning_effort)" if empties else ""
        print(f"{len(got)} sample(s), {out_tok} out tok{note}")
        samples.extend(got)

    # dedup (never silent)
    kept, dropped = sg.dedup(samples, jaccard_threshold=args.jaccard)
    print(f"\ndedup: kept {len(kept)}/{len(samples)}, dropped {len(dropped)}")
    for d in dropped:
        matched = f" ~ #{d.matched_index}" if d.matched_index is not None else ""
        sim = f" (jaccard {d.similarity})" if d.similarity is not None else ""
        print(f"  - dropped #{d.index} [{d.model}] {d.reason}{matched}{sim}: {d.preview}")

    if not kept:
        sys.exit("\nnothing kept after dedup — no corpus written.")

    # write raw.txt + manifest.json
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
    sg.write_corpus(kept, corpus_path)
    manifest = sg.build_manifest(samples, kept, dropped, prompt=prompt,
                                 params=params, base=args.base)
    sg.write_manifest(manifest, manifest_path)

    chars = manifest["counts"]["corpus_chars"]
    print(f"\nwrote {len(kept)} docs ({chars:,} chars) -> {corpus_path}")
    print(f"wrote provenance manifest        -> {manifest_path}")
    print("\nnext: cd <project> && python prepare.py   # raw.txt is a drop-in")


if __name__ == "__main__":
    main()
