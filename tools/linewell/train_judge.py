"""
Train the learned linewell judge (experiment 12): three arms, one human test set.

Arms -- the same tiny encoder (tools/tinyenc) over the well's tokenizer,
seeing the poem-so-far, a separator, and the candidate line:
  llm-only    trained on the local-LLM verdict log
  human-only  trained on N human verdicts (default 100)
  llm+human   trained on the LLM log, then fine-tuned on the same N human verdicts
Every arm is scored on the same held-out human verdicts (held out by poem).

Baselines on the same test set: majority class, a one-feature logistic
regression on the candidate's NLL (the band judge with a learned threshold),
the band judge itself, and -- if --llm_on_test is given -- the local LLM
judge re-run on the test candidates.

    uv run --with tokenizers python tools/linewell/train_judge.py \
        --human tools/linewell/evidence/2026-09-12-judge/claude-log.jsonl \
        --llm tools/linewell/evidence/2026-09-12-judge/llm-log.jsonl \
        --out tools/linewell/evidence/2026-09-12-judge/results.json --llm_on_test
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))

from compose import DEFAULT_MODEL_DIR, _find_tokenizer  # noqa: E402
from tinyenc import Encoder, auroc, evaluate, fit, train_classifier  # noqa: E402

VOCAB = 1024
SEP = VOCAB          # separator between poem-so-far and candidate
PAD = VOCAB + 1


def read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def encode(tok, rec, max_ctx_tokens=192):
    ctx = "\n".join(rec["context"]) + "\n" if rec["context"] else "\n"
    ids = tok.encode(ctx).ids[-max_ctx_tokens:] + [SEP] + tok.encode(rec["line"]).ids
    return {"ids": ids, "label": int(bool(rec["accepted"])), "nll": rec["nll"]}


def logistic_1d(train, test):
    """One-feature logistic regression on NLL, fit by gradient descent."""
    x = torch.tensor([d["nll"] for d in train])
    y = torch.tensor([float(d["label"]) for d in train])
    mu, sd = x.mean(), x.std().clamp(min=1e-6)
    w = torch.zeros(1, requires_grad=True)
    b = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([w, b], max_iter=200)
    def closure():
        opt.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(((x - mu) / sd) * w + b, y)
        loss.backward()
        return loss
    opt.step(closure)
    xt = torch.tensor([d["nll"] for d in test])
    p = torch.sigmoid(((xt - mu) / sd) * w + b).detach().tolist()
    labels = [d["label"] for d in test]
    acc = sum(int((pi > 0.5) == bool(yi)) for pi, yi in zip(p, labels)) / len(labels)
    return {"acc": acc, "auroc": auroc(p, labels)}


def band_baseline(test, lo, hi):
    pred = [lo <= d["nll"] <= hi for d in test]
    labels = [d["label"] for d in test]
    return {"acc": sum(int(p == bool(y)) for p, y in zip(pred, labels)) / len(labels),
            "auroc": auroc([float(p) for p in pred], labels)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--human", required=True)
    ap.add_argument("--llm", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model_dir", default=DEFAULT_MODEL_DIR)
    ap.add_argument("--test_n", type=int, default=200, help="human verdicts held out (by poem)")
    ap.add_argument("--finetune_n", type=int, default=100)
    ap.add_argument("--band_lo", type=float, default=2.3)
    ap.add_argument("--band_hi", type=float, default=3.5)
    ap.add_argument("--epochs_llm", type=int, default=8)
    ap.add_argument("--epochs_human", type=int, default=20)
    ap.add_argument("--seeds", type=int, default=3, help="repeat each arm over this many seeds")
    ap.add_argument("--llm_on_test", action="store_true", help="re-run the local LLM judge on the test set")
    ap.add_argument("--llm_model", default="olmo-3-7b-instruct")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--export", default=None, help="export the best arm to this ONNX path")
    a = ap.parse_args()

    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(_find_tokenizer(a.model_dir))
    human = read_jsonl(a.human)
    llm = read_jsonl(a.llm)
    seen = {(tuple(r["context"]), r["line"]) for r in human}
    llm_clean = [r for r in llm if (tuple(r["context"]), r["line"]) not in seen]
    print(f"human {len(human)} verdicts, llm {len(llm)} ({len(llm) - len(llm_clean)} removed as overlap)")

    # --- split human verdicts by poem: fill the test set poem by poem ---
    rng = random.Random(0)
    pids = sorted({r["pid"] for r in human})
    rng.shuffle(pids)
    test_pids, n = [], 0
    for p in pids:
        if n >= a.test_n:
            break
        test_pids.append(p)
        n += sum(1 for r in human if r["pid"] == p)
    test_recs = [r for r in human if r["pid"] in test_pids]
    rest_recs = [r for r in human if r["pid"] not in test_pids]
    rng.shuffle(rest_recs)
    ft_recs = rest_recs[: a.finetune_n]
    test = [encode(tok, r) for r in test_recs]
    ft = [encode(tok, r) for r in ft_recs]
    rest_all = [encode(tok, r) for r in rest_recs]
    rng.shuffle(llm_clean)
    cut = max(1, len(llm_clean) // 10)
    llm_dev = [encode(tok, r) for r in llm_clean[:cut]]
    llm_train = [encode(tok, r) for r in llm_clean[cut:]]
    print(f"test {len(test)} (poems {sorted(test_pids)}), finetune {len(ft)}, rest {len(rest_all)}, "
          f"llm train {len(llm_train)} dev {len(llm_dev)}")
    labels = [d["label"] for d in test]
    results = {"n_test": len(test), "test_pids": test_pids, "keep_rate_test": sum(labels) / len(labels),
               "n_finetune": len(ft), "n_llm_train": len(llm_train), "arms": {}, "baselines": {}}

    # --- baselines ---
    maj = max(sum(labels), len(labels) - sum(labels)) / len(labels)
    results["baselines"]["majority"] = {"acc": maj}
    results["baselines"]["nll_logistic_on_finetune"] = logistic_1d(ft, test)
    results["baselines"]["nll_logistic_on_rest"] = logistic_1d(rest_all, test)
    results["baselines"]["band"] = band_baseline(test, a.band_lo, a.band_hi)
    if a.llm_on_test:
        from compose import LLMJudge
        judge = LLMJudge(a.llm_model)
        pred = [judge(r["context"], r["line"], r["nll"])[0] for r in test_recs]
        results["baselines"]["llm_judge"] = {
            "acc": sum(int(p == bool(y)) for p, y in zip(pred, labels)) / len(labels),
            "auroc": auroc([float(p) for p in pred], labels),
            "keep_rate": sum(pred) / len(pred)}
    print("baselines", json.dumps(results["baselines"], indent=1))

    # --- arms ---
    def fresh():
        return Encoder(VOCAB + 1, 2, d=128, n_layer=2, n_head=4, max_len=320, dropout=0.1)

    best_model, best_score, best_name = None, -1, None
    arms = {"llm-only": [], "human-only": [], "llm+human": [], "human-all(post-hoc)": []}
    for s in range(a.seeds):
        m = fresh()
        train_classifier(m, llm_train, llm_dev, a.device, 2, epochs=a.epochs_llm, seed=s, log=lambda *_: None)
        r = evaluate(m, test, a.device, 2)
        arms["llm-only"].append({"acc": r["acc"], "auroc": r["auroc"]})
        m2 = fresh()
        m2.load_state_dict(m.state_dict())
        fit(m2, ft, a.device, 2, epochs=a.epochs_human, lr=1e-4, seed=s, log=lambda *_: None)
        r2 = evaluate(m2, test, a.device, 2)
        arms["llm+human"].append({"acc": r2["acc"], "auroc": r2["auroc"]})
        m3 = fresh()
        fit(m3, ft, a.device, 2, epochs=a.epochs_human, seed=s, log=lambda *_: None)
        r3 = evaluate(m3, test, a.device, 2)
        arms["human-only"].append({"acc": r3["acc"], "auroc": r3["auroc"]})
        m4 = fresh()
        fit(m4, rest_all, a.device, 2, epochs=a.epochs_human, seed=s, log=lambda *_: None)
        r4 = evaluate(m4, test, a.device, 2)
        arms["human-all(post-hoc)"].append({"acc": r4["acc"], "auroc": r4["auroc"]})
        for name, res, model in (("llm-only", r, m), ("llm+human", r2, m2), ("human-only", r3, m3)):
            if res["auroc"] == res["auroc"] and res["auroc"] > best_score:
                best_score, best_model, best_name = res["auroc"], model, name
        print(f"seed {s}: llm-only {r['auroc']:.3f}  llm+human {r2['auroc']:.3f}  "
              f"human-only {r3['auroc']:.3f}  human-all {r4['auroc']:.3f}  (auroc)")
    for name, runs in arms.items():
        accs = [x["acc"] for x in runs]
        aus = [x["auroc"] for x in runs]
        results["arms"][name] = {"runs": runs, "acc_mean": sum(accs) / len(accs), "auroc_mean": sum(aus) / len(aus)}
    results["best_arm"] = best_name
    print(json.dumps({k: {"acc": round(v["acc_mean"], 3), "auroc": round(v["auroc_mean"], 3)}
                      for k, v in results["arms"].items()}, indent=1))
    with open(a.out, "w") as f:
        json.dump(results, f, indent=1)
    if a.export and best_model is not None:
        best_model.eval().cpu()
        dummy = torch.full((1, 64), PAD, dtype=torch.long)
        dummy[0, :10] = torch.arange(10)
        torch.onnx.export(best_model, (dummy,), a.export, input_names=["ids"], output_names=["logits"],
                          dynamic_axes={"ids": {0: "batch", 1: "len"}}, opset_version=17)
        print(f"exported {best_name} -> {a.export} ({os.path.getsize(a.export) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
