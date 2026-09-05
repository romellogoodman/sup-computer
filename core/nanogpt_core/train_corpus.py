"""Train a small GPT on any text file — one command, one run dir.

    uv run sup-train ./corpus.txt [--out DIR] [--size tiny|small|medium] [--iters N]
                                  [--tokenizer char|bpe] [--name NAME] [--device DEV]
                                  [--no-export]

Five steps, each printed as it runs:

  prepare   90/10 split into <out>/data/corpus/{train,val}.bin + meta.pkl —
            the tokenizer contract every core script keys off (ADR-0012)
  train     core's train.py as a subprocess, driven by the resolved config
            written to <out>/config.py (so the run reproduces by hand)
  sample    three samples via the library surface (ADR-0029) -> samples.txt
  export    model.py snapshotted beside ckpt.pt, then core/export/export.py
            -> <out>/dist/<name>.onnx (+ int8, tokenizer sidecar, manifest)
  card      <out>/MODEL_CARD.md in the studio's model-card shape, real
            numbers filled in, human-only sections marked TODO

The result is a *run*, not a release: releasing still follows
docs/handbook.md § Releasing a version. The Node CLI's `sup train`
subcommand (cli/) spawns this entry point.
"""

import argparse
import json
import os
import pickle
import re
import shlex
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))  # core/nanogpt_core/
TRAIN = os.path.join(HERE, "train.py")
MODEL = os.path.join(HERE, "model.py")
EXPORT = os.path.join(os.path.dirname(HERE), "export", "export.py")

DATASET = "corpus"  # <out>/data/<DATASET>/ — train.py's data_root/dataset pair
SIZES = {
    "tiny": dict(n_layer=4, n_head=4, n_embd=128, block_size=128, batch_size=32),
    "small": dict(n_layer=6, n_head=6, n_embd=192, block_size=256, batch_size=32),
    "medium": dict(n_layer=6, n_head=6, n_embd=384, block_size=256, batch_size=32),
}
BPE_VOCAB = 1024  # the shakespeare-nanogpt-3 recipe: byte-level, lossless
PROMPT_CHARS = 80  # the demo prompt is the corpus's first line, capped here
NUM_SAMPLES = 3
SAMPLE_TOKENS = 200
TEMPERATURE = 0.8
SEPARATOR = "---------------"


def step(title):
    print(f"\n== {title} ==", flush=True)


def die(msg):
    sys.exit(f"sup-train: {msg}")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "corpus"


# ----------------------------------------------------------------------------
# prepare


def read_corpus(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except UnicodeDecodeError as e:
        die(f"{path} is not UTF-8 text ({e}); sup-train reads plain text files")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        die(f"{path} is empty")
    return text


def first_line(text):
    """The corpus's first non-empty line, leading whitespace kept (it puts a
    model in its corpus's format — registry.json's demo.prompt rule)."""
    for line in text.split("\n"):
        if line.strip():
            return line[:PROMPT_CHARS]
    return text[:PROMPT_CHARS]


def train_bpe(train_text, save_path):
    try:
        from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
    except ImportError:
        die("--tokenizer bpe needs the `tokenizers` library: uv sync --extra hf")
    tok = Tokenizer(models.BPE(unk_token=None))
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(
        vocab_size=BPE_VOCAB,
        special_tokens=[],
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),  # all 256 bytes -> no UNK
        show_progress=False,
    )
    tok.train_from_iterator([train_text], trainer=trainer)
    tok.save(save_path)
    return tok


def prepare(text, data_dir, tokenizer):
    """Write the meta.pkl dataset contract; returns (meta, n_train, n_val)."""
    os.makedirs(data_dir, exist_ok=True)
    n = len(text)
    train_text, val_text = text[: int(n * 0.9)], text[int(n * 0.9):]

    if tokenizer == "char":
        chars = sorted(set(text))
        stoi = {c: i for i, c in enumerate(chars)}
        itos = {i: c for i, c in enumerate(chars)}
        meta = {"vocab_size": len(chars), "stoi": stoi, "itos": itos}

        def encode(s):
            return np.fromiter((stoi[c] for c in s), dtype=np.uint16, count=len(s))

    else:
        tok = train_bpe(train_text, os.path.join(data_dir, "tokenizer.json"))
        meta = {"vocab_size": tok.get_vocab_size(), "tokenizer": "tokenizer.json"}

        def encode(s):
            return np.array(tok.encode(s).ids, dtype=np.uint16)

    if meta["vocab_size"] > 65535:
        die(f"vocab of {meta['vocab_size']} exceeds uint16 — the dataset contract caps at 65535 tokens")

    train_ids, val_ids = encode(train_text), encode(val_text)
    train_ids.tofile(os.path.join(data_dir, "train.bin"))
    val_ids.tofile(os.path.join(data_dir, "val.bin"))
    with open(os.path.join(data_dir, "meta.pkl"), "wb") as f:
        pickle.dump(meta, f)

    print(f"corpus: {n:,} characters, {text.count(chr(10)) + 1:,} lines")
    print(f"tokenizer: {tokenizer}, vocab size {meta['vocab_size']}")
    print(f"train: {len(train_ids):,} tokens   val: {len(val_ids):,} tokens")
    print(f"wrote train.bin / val.bin / meta.pkl -> {data_dir}")
    return meta, len(train_ids), len(val_ids)


# ----------------------------------------------------------------------------
# train


def build_config(size, iters, device, out_dir, data_root):
    """Every knob train.py will see, resolved. Keys are train.py globals: the
    file this becomes is exec'd by its configurator."""
    return dict(
        out_dir=out_dir,
        data_root=data_root,
        dataset=DATASET,
        **SIZES[size],
        gradient_accumulation_steps=1,
        dropout=0.1,
        bias=False,
        learning_rate=1e-3,
        min_lr=1e-4,
        beta2=0.99,
        max_iters=iters,
        lr_decay_iters=iters,
        warmup_iters=max(1, min(100, iters // 20)),
        eval_interval=max(1, iters // 10),
        eval_iters=max(4, min(100, iters // 10)),
        log_interval=max(1, iters // 100),
        always_save_checkpoint=False,  # keep the best-val checkpoint, not the last
        device=device,
        dtype="float32",
        compile=False,
        seed=1337,
    )


def write_config(path, cfg, corpus):
    lines = [
        "# Resolved training config written by sup-train — the whole run in one file.",
        f"# corpus: {corpus}",
        "# Re-run by hand from the repo root:",
        f"#   uv run python core/nanogpt_core/train.py {path}",
        "",
    ]
    lines += [f"{k} = {v!r}" for k, v in cfg.items()]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def train(config_path):
    sys.stdout.flush()
    t0 = time.time()
    proc = subprocess.run([sys.executable, TRAIN, config_path])
    if proc.returncode != 0:
        die(f"train.py exited with code {proc.returncode} — see its output above")
    return time.time() - t0


# ----------------------------------------------------------------------------
# sample


def sample(out_dir, data_root, device, prompt):
    import torch

    from nanogpt_core.checkpoint import load_model, load_tokenizer

    torch.manual_seed(1337)
    model, ckpt = load_model(out_dir, device)
    tok = load_tokenizer(ckpt, data_root)
    x = torch.tensor(tok.encode(prompt), dtype=torch.long, device=device)[None, ...]
    outs = []
    with torch.no_grad():
        for _ in range(NUM_SAMPLES):
            y = model.generate(x, SAMPLE_TOKENS, temperature=TEMPERATURE, top_k=200)
            outs.append(tok.decode(y[0].tolist()))
    text = f"\n{SEPARATOR}\n".join(outs) + "\n"
    path = os.path.join(out_dir, "samples.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"wrote {path}")
    return model, ckpt, outs


# ----------------------------------------------------------------------------
# export


def export(out_dir, name, data_dir, meta):
    """Give the run dir the shape of a frozen release (model.py + ckpt.pt +
    meta.pkl side by side) and run the parity-checked exporter on it."""
    shutil.copyfile(MODEL, os.path.join(out_dir, "model.py"))
    shutil.copyfile(os.path.join(data_dir, "meta.pkl"), os.path.join(out_dir, "meta.pkl"))
    if "tokenizer" in meta:
        shutil.copyfile(os.path.join(data_dir, meta["tokenizer"]), os.path.join(out_dir, meta["tokenizer"]))
    dist = os.path.join(out_dir, "dist")
    sys.stdout.flush()
    # importing the snapshotted model.py would otherwise leave a __pycache__ in the run dir
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run([sys.executable, EXPORT, out_dir, dist, "--name", name], env=env)
    if proc.returncode != 0:
        die(f"export.py exited with code {proc.returncode} — see its output above")
    return dist


# ----------------------------------------------------------------------------
# card stub


def fmt_secs(s):
    return f"{s:.0f}s" if s < 90 else f"{s / 60:.1f} min"


def registry_entry(r):
    return {
        "id": r["name"],
        "project": "TODO",
        "version": 1,
        "git_tag": "TODO",
        "architecture": "modern (RoPE, RMSNorm, bias-free)",
        "tagline": "TODO",
        "researcher": "TODO",
        "tokenizer": {"type": r["tokenizer"], "vocab_size": r["vocab_size"]},
        "params": r["params"],
        "block_size": r["cfg"]["block_size"],
        "held_out_bpc": None,
        "frozen_code": "TODO",
        "model_card": "TODO",
        "artifacts": {"checkpoint": None, "onnx": None, "onnx_int8": None},
        "demo": {"prompt": r["prompt"]},
    }


def write_card(path, r):
    cfg = r["cfg"]
    kind = "character" if r["tokenizer"] == "char" else "byte-level BPE"
    shape = f"{cfg['n_layer']}L/{cfg['n_head']}H/{cfg['n_embd']}E, block {cfg['block_size']}"
    val_bits = r["best_val_loss"] / np.log(2)
    per = "bits per character" if r["tokenizer"] == "char" else "bits per token"
    rerun = (
        f"uv run sup-train {shlex.quote(r['corpus'])} --out {shlex.quote(r['out'])} "
        f"--size {r['size']} --iters {r['iters']} --tokenizer {r['tokenizer']} --name {r['name']}"
    )
    sample_cmd = (
        f"uv run python core/nanogpt_core/sample.py --out_dir={shlex.quote(r['out'])} "
        f"--data_root={shlex.quote(r['data_root'])} --start={shlex.quote(r['prompt'])}"
    )
    samples = "\n".join(f"> {line}" for line in r["samples"][0].rstrip("\n").split("\n"))
    card = f"""---
license: mit
library_name: nanogpt
pipeline_tag: text-generation
tags:
  - {r['name']}
  - nanogpt
  - {'char-level' if r['tokenizer'] == 'char' else 'bpe'}
  - gpt
---

# Model Card — `{r['name']}`

<!-- A stub written by sup-train. The numbers are real; every TODO is a line
only the person who knows this corpus can write. This is a run, not a
release: releasing follows docs/handbook.md § Releasing a version. -->

## What it is

A {kind} GPT trained from scratch on `{os.path.basename(r['corpus'])}` ({r['chars']:,} characters).
{r['params'] / 1e6:.2f}M params ({shape}) over a {r['vocab_size']}-token vocabulary.
TODO: what the corpus is, and what this model is for.

## Training data

`{r['corpus']}` — {r['chars']:,} characters, {r['lines']:,} lines, split 90/10 into {r['n_train']:,} train and {r['n_val']:,} validation tokens ({r['tokenizer']} tokenizer, vocab {r['vocab_size']}).
TODO: where the text came from and its license.

## Training

{cfg['n_layer']} layers, {cfg['n_head']} heads, {cfg['n_embd']} embed, block {cfg['block_size']}, dropout {cfg['dropout']}, batch {cfg['batch_size']}; {r['iters']:,} steps at lr {cfg['learning_rate']} (warmup {cfg['warmup_iters']}, cosine to {cfg['min_lr']}) on {r['device']}, {fmt_secs(r['train_secs'])}.
Best-val checkpointing: the checkpoint is the step with the lowest validation loss (step {r['iter_num']:,}), not the last.

## Numbers

| Metric | value |
|---|---|
| params | {r['params']:,} |
| vocab size | {r['vocab_size']} ({r['tokenizer']}) |
| block size | {cfg['block_size']} |
| training steps | {r['iters']:,} |
| best val loss | {r['best_val_loss']:.3f} nats/token ({val_bits:.3f} {per}) at step {r['iter_num']:,} |
| wall-clock (train) | {fmt_secs(r['train_secs'])} on {r['device']} |

The validation loss is scored on the corpus's own last 10% — not a held-out test in the studio's sense, so it is not comparable to the BPC column in `registry.json`.
TODO: an eval that measures what the loss cannot.

## Samples

Temperature {TEMPERATURE}, prompted with the corpus's first line. All three are in `samples.txt`; the first:

{samples}

## Limitations

- One seed, one run. Nothing here is averaged.
- Scored on a slice of its own corpus; there is no held-out test.
- A {r['params'] / 1e6:.2f}M-param model memorizes a small corpus quickly — check the samples against the source before calling anything generation.
- TODO: what it gets wrong, with a mechanism.

## Reproduce

From the repo root:

```bash
{rerun}
# or step by step — the resolved config is the run:
uv run python core/nanogpt_core/train.py {r['config_path']}
{sample_cmd}
```

## Registry entry

A `registry.json` entry to fill in if this run is ever released:

```json
{json.dumps(registry_entry(r), indent=2, ensure_ascii=False)}
```
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(card)
    print(f"wrote {path}")


# ----------------------------------------------------------------------------
# main


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        prog="sup-train",
        description="Train a small GPT on a text file: prepare, train, sample, export, card stub.",
    )
    ap.add_argument("corpus", help="a UTF-8 text file")
    ap.add_argument("--out", help="run directory (default: ./runs/<name>)")
    ap.add_argument("--size", choices=list(SIZES), default="small",
                    help="model preset: tiny 4L/128E, small 6L/192E, medium 6L/384E (default: small)")
    ap.add_argument("--iters", type=int, default=2000, help="training steps (default: 2000)")
    ap.add_argument("--tokenizer", choices=["char", "bpe"], default="char",
                    help=f"char (default) or a corpus-trained byte-level BPE (vocab {BPE_VOCAB})")
    ap.add_argument("--name", help="model name for the export + card (default: the corpus file's stem)")
    ap.add_argument("--device", help="cpu, cuda, mps... (default: auto — cuda > mps > cpu)")
    ap.add_argument("--no-export", action="store_true", help="skip the ONNX export")
    args = ap.parse_args(argv)
    if args.iters < 1:
        ap.error("--iters must be at least 1")
    return args


def main(argv=None):
    args = parse_args(argv)
    corpus = os.path.abspath(args.corpus)
    if not os.path.isfile(corpus):
        die(f"no such file: {corpus}")
    name = slug(args.name or os.path.splitext(os.path.basename(corpus))[0])
    out = os.path.abspath(args.out or os.path.join("runs", name))
    data_root = os.path.join(out, "data")
    data_dir = os.path.join(data_root, DATASET)
    total0 = time.time()

    step("prepare")
    text = read_corpus(corpus)
    meta, n_train, n_val = prepare(text, data_dir, args.tokenizer)
    block = SIZES[args.size]["block_size"]
    if n_val <= block:
        die(
            f"corpus too small: the 10% validation split is {n_val} tokens but --size {args.size} "
            f"has a context of {block} tokens; use a longer text (or a smaller --size)"
        )
    prompt = first_line(text)

    step("train")
    from nanogpt_core.checkpoint import pick_device

    device = pick_device(args.device)
    cfg = build_config(args.size, args.iters, device, out, data_root)
    config_path = os.path.join(out, "config.py")
    write_config(config_path, cfg, corpus)
    stale = os.path.join(out, "ckpt.pt")
    if os.path.exists(stale):
        os.remove(stale)  # from scratch means from scratch; a crashed run's ckpt must not be sampled
    print(f"config -> {config_path}   ({args.size}: {SIZES[args.size]}, {args.iters} iters on {device})")
    train_secs = train(config_path)
    if not os.path.exists(stale):
        die("training produced no ckpt.pt")
    print(f"trained in {fmt_secs(train_secs)}")

    step("sample")
    model, ckpt, samples = sample(out, data_root, device, prompt)
    record = dict(
        name=name, corpus=corpus, out=out, data_root=data_root, config_path=config_path,
        size=args.size, iters=args.iters, tokenizer=args.tokenizer, device=device,
        chars=len(text), lines=text.count("\n") + 1, vocab_size=meta["vocab_size"],
        n_train=n_train, n_val=n_val, cfg=cfg, params=model.get_num_params(),
        best_val_loss=float(ckpt["best_val_loss"]), iter_num=int(ckpt["iter_num"]),
        train_secs=train_secs, prompt=prompt, samples=samples,
    )
    del model  # the export subprocess loads its own copy

    dist = None
    if not args.no_export:
        step("export")
        dist = export(out, name, data_dir, meta)

    step("card")
    card_path = os.path.join(out, "MODEL_CARD.md")
    write_card(card_path, record)

    step("done")
    print(f"run dir      {out}")
    print(f"checkpoint   {stale}   (best val loss {record['best_val_loss']:.3f} at step {record['iter_num']:,})")
    print(f"config       {config_path}")
    print(f"samples      {os.path.join(out, 'samples.txt')}")
    if dist:
        print(f"onnx         {os.path.join(dist, name + '.onnx')}   (+ int8, tokenizer sidecar, manifest)")
    print(f"card stub    {card_path}")
    print(f"{fmt_secs(time.time() - total0)} all in. Sample the checkpoint again with:")
    print(
        f"  uv run python core/nanogpt_core/sample.py --out_dir={shlex.quote(out)} "
        f"--data_root={shlex.quote(data_root)} --start={shlex.quote(prompt)}"
    )


if __name__ == "__main__":
    main()
