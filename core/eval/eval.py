"""
Score a trained checkpoint on a fixed held-out test set, in bits-per-character.

Thin CLI over nanogpt_core.bpc (ADR-0029) — harnesses import
`nanogpt_core.bpc.score_run` directly instead of parsing this script's
output. The tokenizer resolves from the dataset's meta.pkl: char stoi/itos,
a corpus-trained HF tokenizer.json (the ADR-0012 seam), or GPT-2 tiktoken
when no meta exists.

This scores the CURRENT (modern: RoPE + RMSNorm + bias-free) architecture only.
Historical base-architecture versions are scored inside their own frozen
projects/<project>/models/<version>/ folder, which vendors its own model.py.

Usage:
  python core/eval/eval.py <out_dir> \
      --test projects/shakespeare/test.txt \
      --data_root projects/shakespeare/data     # for meta.pkl; omit for GPT-2 BPE
"""
import argparse

from nanogpt_core.bpc import score_run


def main(out_dir, test_path, data_root="", device=None):
    r = score_run(out_dir, test_path, data_root, device)
    if r["dropped_chars"]:
        print(f"warning: {r['dropped_chars']} chars not in vocab, excluded from BPC")
    print(
        f"{out_dir}\t"
        f"tokenizer={r['tokenizer']}\ttokens={r['tokens']}\tchars={r['chars']}\t"
        f"token_loss={r['token_loss']:.4f}\tppl={r['ppl']:.2f}\tBPC={r['bpc']:.4f}"
    )
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("out_dir", help="run dir containing ckpt.pt")
    ap.add_argument("--test", required=True, dest="test_path", help="held-out test text")
    ap.add_argument(
        "--data_root",
        "--data-dir",  # the historical spelling, kept as an alias
        default="",
        dest="data_root",
        help="parent dir of <dataset>/meta.pkl; omit for GPT-2 BPE",
    )
    ap.add_argument("--device", default=None, help="override the auto-picked device")
    a = ap.parse_args()
    main(a.out_dir, a.test_path, a.data_root, a.device)
