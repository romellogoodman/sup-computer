"""chat_eval.py -- the conversational eval for the chat arm.

The harness measures free prose; the keyboard UI needs something narrower:
given a user turn, does the model produce a grammatical, non-degenerate
*reply*? Protocol: each prompt is framed exactly as the UI frames it --

    \n- {user turn}\n-

-- and the model generates until it ends the line. k replies per prompt at
temperature 0.8 (the intended UI default; 1.0 reported by --temperature).
Replies face the same oracle as everything else. Also reported: empty/echo
rates and a transcript sample for the log.

Prompts are a fixed, oracle-verified set of everyday user turns (the UI's
real distribution), not corpus lines -- corpus first turns are training data.

Run from the repo root:
    uv run python projects/pona/chat_eval.py --out_dir projects/pona/runs/chat-r1
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "oracle"))
from oracle import check_sentences  # noqa: E402
import pona_tok  # noqa: E402
from checkpoint import load_model  # vendored: no cross-folder imports in a frozen release  # noqa: E402
from harness import load_meta, SENT_SPLIT  # noqa: E402

PROMPTS = [
    "toki! sina pilin seme?",
    "sina moku e seme?",
    "tenpo suno ni li pona ala pona?",
    "sina lon seme?",
    "nimi sina li seme?",
    "mi pilin ike. o pana e pona tawa mi.",
    "sina olin e seme?",
    "soweli li pona ala pona tawa sina?",
    "sina wile pali e seme?",
    "telo li kama anpa. mi pilin ike.",
    "o toki e ijo pona tawa mi.",
    "sina kama sona e toki pona kepeken tenpo seme?",
    "mi wile lape. taso mi ken ala.",
    "kule seme li pona tawa sina?",
    "sina wile tawa ma seme?",
    "jan pona sina li seme?",
    "mi jo e soweli lili. ona li suwi.",
    "sina kute e kalama musi seme?",
    "mi wile moku. o toki e moku pona.",
    "tenpo pimeja ni la sina wile seme?",
]


def gen_replies(model, meta, device, prompt, k, temperature, seed, max_tokens=36):
    torch.manual_seed(seed)
    stoi, itos = meta["stoi"], meta["itos"]
    framed = f"\n- {prompt}\n- "
    ids = pona_tok.encode(framed, stoi)
    idx = torch.tensor([ids] * k, dtype=torch.long, device=device)
    with torch.no_grad():
        out = model.generate(idx, max_tokens, temperature=temperature, top_k=None)
    nl = stoi["\n"]
    replies = []
    for r in range(k):
        tail = out[r, len(ids):].tolist()
        if nl in tail:
            tail = tail[:tail.index(nl)]
        replies.append(pona_tok.detok([itos[i] for i in tail]).strip())
    return replies


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--k", type=int, default=8, help="replies per prompt")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--device", default="mps")
    args = ap.parse_args()

    model, checkpoint = load_model(args.out_dir, args.device)
    model.eval()
    meta = load_meta(checkpoint)
    assert meta.get("arm") == "word", "chat_eval expects a word-arm checkpoint"
    tag = os.path.basename(os.path.normpath(args.out_dir))

    # sanity: the prompt set itself must pass the oracle
    prompt_check = check_sentences([s for p in PROMPTS for s in SENT_SPLIT.split(p)])
    bad_prompts = sum(1 for r in prompt_check if any(e["category"] == "error" for e in r["errors"]))
    assert bad_prompts == 0, "prompt set failed the oracle — fix the prompts first"

    rows = []
    for i, prompt in enumerate(PROMPTS):
        replies = gen_replies(model, meta, args.device, prompt, args.k,
                              args.temperature, args.seed + i)
        rows.extend({"prompt": prompt, "reply": r.replace("<name>", "Mewi")}
                    for r in replies)

    n = len(rows)
    empty = sum(1 for r in rows if not r["reply"])
    echo = sum(1 for r in rows if r["reply"] and r["reply"].lower() == r["prompt"].lower())
    scored = [r for r in rows if r["reply"]]
    sentences, owner = [], []
    for j, r in enumerate(scored):
        for s in SENT_SPLIT.split(r["reply"]):
            s = s.strip()
            if len(s) >= 2:
                sentences.append(s)
                owner.append(j)
    results = check_sentences(sentences)
    reply_bad = set()
    taxonomy = Counter()
    for j, res in zip(owner, results):
        for e in res["errors"]:
            taxonomy[f"{e['category']}:{e['rule']}"] += 1
            if e["category"] == "error":
                reply_bad.add(j)
    gram = 1 - len(reply_bad) / len(scored) if scored else 0.0
    uniq = len(set(r["reply"].lower() for r in scored)) / len(scored) if scored else 0.0
    mean_words = (sum(len(re.findall(r"[a-zA-Z]+", r["reply"])) for r in scored) / len(scored)
                  if scored else 0.0)

    report = {
        "tag": tag, "temperature": args.temperature, "k": args.k,
        "prompts": len(PROMPTS), "replies": n,
        "reply_grammaticality_error_only": gram,
        "empty_rate": empty / n, "echo_rate": echo / n,
        "unique_reply_rate": uniq, "mean_reply_words": mean_words,
        "taxonomy_top": dict(taxonomy.most_common(15)),
        "transcript": rows[:60],
    }
    out_path = os.path.join(HERE, "research", f"eval-{tag}-replies-t{args.temperature}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"[{tag}] reply grammaticality (error-only): {gram:.1%}  "
          f"empty {empty / n:.1%}  echo {echo / n:.1%}  unique {uniq:.1%}  "
          f"mean {mean_words:.1f} words")
    for r in rows[:8]:
        print(f"  > {r['prompt']}\n  < {r['reply']}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
