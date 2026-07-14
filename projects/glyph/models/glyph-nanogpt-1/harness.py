"""
harness.py -- sample glyphs from a checkpoint and measure what the loss can't.

Quality checks stay OUT of the loss metric (house rule): BPC comes from
core/eval/eval.py; this measures the sampled artifact itself, per letter:

  parse rate      strict grammar validity (codec.decode_glyph) -- covers
                  closure (Z), coordinate pairing, contour structure
  unterminated    sample never emitted a glyph boundary within the budget
  memorization    exact-line matches against the letter's TRAIN split --
                  with corpora this small, regurgitation is the first
                  failure mode, so it's measured, not assumed away

Also renders a specimen sheet of the samples (valid glyphs drawn, invalid
slots marked) to research/samples/, and writes the metrics JSON into the
run dir. Recorded, not gated -- pilot thresholds get set after seeing
numbers, not invented before.

Usage (repo root):
  uv run python projects/glyph/harness.py projects/glyph/runs/pilot-a-r1 \
      --letters a --num 64 --temp 1.0
"""
import argparse
import json
import os
import pickle
import sys

import torch

from model import GPTConfig, GPT  # vendored: no cross-folder imports

HERE = os.path.dirname(os.path.abspath(__file__))
import codec  # noqa: E402  (vendored alongside)
from prepare import split_of  # noqa: E402  (family-split assignment, shared)

MAX_GLYPH_TOKENS = 350  # p99 real glyph is 275 tokens; anything longer is lost


def load_model(out_dir, device):
    ckpt = torch.load(os.path.join(out_dir, "ckpt.pt"), map_location=device, weights_only=True)
    model = GPT(GPTConfig(**ckpt["model_args"]))
    sd = ckpt["model"]
    for k in list(sd):
        if k.startswith("_orig_mod."):
            sd[k[len("_orig_mod."):]] = sd.pop(k)
    model.load_state_dict(sd)
    model.eval().to(device)
    return model, ckpt


def train_lines(letter):
    """The letter's train-split lines, rebuilt exactly as prepare.py splits."""
    out = set()
    with open(os.path.join(HERE, "corpus", f"{letter}.txt")) as f:
        for row in f:
            family_dir, _, line = row.rstrip("\n").split("\t")
            if split_of(family_dir) == "train":
                out.add(line)
    return out


def sample_letter(model, stoi, itos, letter, num, temp, device):
    """Generate num glyphs conditioned on the letter. Prompt is '\\n<letter>'
    -- in training, a letter token always follows a glyph boundary."""
    prompt = torch.tensor([[stoi["\n"], stoi[letter]]] * num, dtype=torch.long, device=device)
    with torch.no_grad():
        out = model.generate(prompt, MAX_GLYPH_TOKENS, temperature=temp)
    results = []
    for row in out:
        text = "".join(itos[int(t)] for t in row[1:])  # keep the letter, drop the \n
        results.append(text.split("\n")[0] if "\n" in text else None)
    return results


def sheet_html(title, blocks):
    cells = []
    for label, samples in blocks:
        svgs = []
        for line in samples:
            if line is None:
                svgs.append('<div class="bad">&empty;</div>')  # unterminated
                continue
            try:
                g = codec.decode_glyph(line)
            except codec.GlyphSyntaxError:
                svgs.append('<div class="bad">&times;</div>')  # parse failure
                continue
            d = codec.glyph_to_svg_path(g)
            svgs.append(f'<svg viewBox="-64 -1100 1152 1700"><g transform="scale(1,-1)">'
                        f'<path d="{d}" fill="#111" fill-rule="evenodd"/></g></svg>')
        cells.append(f'<h2>{label}</h2><div class="grid">{"".join(svgs)}</div>')
    return f"""<!doctype html><meta charset="utf-8"><title>{title}</title>
<style>
  body {{ font: 13px system-ui; margin: 2rem auto; max-width: 900px; }}
  .grid {{ display: grid; grid-template-columns: repeat(8, 1fr); gap: 6px; }}
  svg {{ width: 100%; background: #f6f6f6; }}
  .bad {{ display: flex; align-items: center; justify-content: center;
          background: #fdecec; color: #b33; aspect-ratio: 1152/1700; }}
</style><h1>{title}</h1>{"".join(cells)}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--letters", required=True, help="e.g. 'a' or 'aeg'")
    ap.add_argument("--num", type=int, default=64)
    ap.add_argument("--temp", type=float, default=1.0)
    args = ap.parse_args()

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model, ckpt = load_model(args.out_dir, device)
    meta_path = os.path.join(HERE, ckpt["config"]["dataset"], "meta.pkl")
    meta = pickle.load(open(meta_path, "rb"))
    stoi, itos = meta["stoi"], meta["itos"]

    run = os.path.basename(os.path.normpath(args.out_dir))
    report, blocks = {"run": run, "temp": args.temp, "num": args.num, "letters": {}}, []
    for letter in args.letters:
        samples = sample_letter(model, stoi, itos, letter, args.num, args.temp, device)
        train = train_lines(letter)
        parsed, memorized, unterminated = 0, 0, 0
        for line in samples:
            if line is None:
                unterminated += 1
                continue
            try:
                g = codec.decode_glyph(line)
                parsed += 1 if g["letter"] == letter else 0
            except codec.GlyphSyntaxError:
                continue
            if line in train:
                memorized += 1
        report["letters"][letter] = {
            "parse_rate": round(parsed / args.num, 3),
            "unterminated": unterminated,
            "memorized_exact": memorized,
            "memorized_rate": round(memorized / args.num, 3),
        }
        blocks.append((f"{letter} — parse {parsed}/{args.num}, "
                       f"memorized {memorized}, unterminated {unterminated}", samples))
        print(f"{run} {letter}: parse {parsed}/{args.num}  "
              f"memorized {memorized}  unterminated {unterminated}")

    with open(os.path.join(args.out_dir, f"harness-{args.letters}.json"), "w") as f:
        json.dump(report, f, indent=1)
    # raw sampled lines are report material (specimen assets) -- keep them.
    # one sample per line; unterminated samples marked with a bare "!".
    with open(os.path.join(args.out_dir, f"samples-{args.letters}-t{args.temp}.txt"), "w") as f:
        for _, samples in blocks:
            f.write("".join((line if line is not None else "!") + "\n" for line in samples))
    sheets = os.path.join(HERE, "samples")
    os.makedirs(sheets, exist_ok=True)
    out = os.path.join(sheets, f"{run}-{args.letters}-t{args.temp}.html")
    with open(out, "w") as f:
        f.write(sheet_html(f"{run} @ temp {args.temp}", blocks))
    print(f"sheet -> {os.path.relpath(out)}")


if __name__ == "__main__":
    main()
