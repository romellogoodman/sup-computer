"""
Snapshot Claude's cumulative token usage for this Claude Code session, by
parsing the session transcript (~/.claude/projects/<proj>/<session>.jsonl).

Used by the LLM-assisted research loop to measure the "researcher cost" of each round: snapshot
before and after a round, and the delta is the tokens Claude burned to produce
that round's improvement.

Usage:
  python research-lab/claude_cost.py            # newest session in this project
  python research-lab/claude_cost.py <file>     # a specific transcript
"""
import json
import os
import sys
import glob

PROJ_DIR = os.path.expanduser("~/.claude/projects/-Users-romello-code")


def newest_transcript():
    files = glob.glob(os.path.join(PROJ_DIR, "*.jsonl"))
    return max(files, key=os.path.getmtime) if files else None


def totals(path):
    out = cr = cc = inp = 0
    for line in open(path):
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
    t = totals(path)
    print(f"transcript: {os.path.basename(path)}")
    for k in ("output", "input", "cache_creation", "cache_read", "all_in"):
        print(f"  {k:<15} {t[k]:>14,}")
