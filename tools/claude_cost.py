"""
Researcher-cost snapshot: token usage of the current Claude Code session transcript.
Parses the session's jsonl under ~/.claude/projects/ to sum cumulative tokens.

Used by the LLM-assisted research loop to measure the "researcher cost" of each round: snapshot
before and after a round, and the delta is the tokens Claude burned to produce
that round's improvement.

Usage:
  uv run python tools/claude_cost.py            # newest session in this project
  uv run python tools/claude_cost.py <file>     # a specific transcript
"""
import json
import os
import sys
import glob


def proj_dir():
    # Claude Code stores transcripts under a slug derived from the cwd with
    # '/' -> '-'; deriving it (instead of hardcoding) keeps this portable and
    # pointed at *this* repo's sessions no matter who runs it or from where.
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    slug = repo.replace(os.sep, "-")
    return os.path.expanduser(os.path.join("~", ".claude", "projects", slug))


def newest_transcript():
    files = glob.glob(os.path.join(proj_dir(), "*.jsonl"))
    return max(files, key=os.path.getmtime) if files else None


def totals(path):
    out = cr = cc = inp = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            u = (o.get("message") or {}).get("usage") or o.get("usage")
            if not u:
                continue
            inp += u.get("input_tokens", 0)
            out += u.get("output_tokens", 0)
            cr += u.get("cache_read_input_tokens", 0)
            cc += u.get("cache_creation_input_tokens", 0)
    return {
        "output": out,                  # tokens Claude generated (core work)
        "input": inp,                   # fresh (uncached) input
        "cache_creation": cc,           # new context cached
        "cache_read": cr,               # cheap repeated context reads
        "all_in": inp + out + cr + cc,  # full footprint
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else newest_transcript()
    if not path or not os.path.exists(path):
        sys.exit(f"no transcript found (looked in {proj_dir()})")
    t = totals(path)
    print(f"transcript: {os.path.basename(path)}")
    for k in ("output", "input", "cache_creation", "cache_read", "all_in"):
        print(f"  {k:<15} {t[k]:>14,}")
