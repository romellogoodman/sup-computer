"""
mf_sweep.py -- generate a corpus by sweeping Computer Modern's parameters.

Knuth's cmss10.mf/cmr10.mf are ~62 named values followed by `generate roman`.
This takes one of those files as an anchor, perturbs a chosen subset, compiles
each setting through mf2pt1 (Metafont -> MetaPost -> Type 1), and encodes the
lowercase glyphs with glyph's own codec so the result is byte-comparable with
the google/fonts corpus.

Two sweep modes:
  axes   -- four coordinated multipliers (weight, width, x-height, slant),
            which is roughly what a variable font's axes give you
  indep  -- every parameter jittered independently, which is what "62 knobs"
            would mean if the knobs were actually independent

Settings that fail to compile are counted, not hidden: the yield is a finding.
"""
import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "projects", "glyph", "data"))
import codec  # noqa: E402
from fontTools import t1Lib  # noqa: E402
from fontTools.misc import eexec, psCharStrings, psLib  # noqa: E402
from fontTools.pens.cu2quPen import Cu2QuPen  # noqa: E402
from pathops import Path as SkPath  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEXBIN = os.environ.get("TEXBIN", os.path.expanduser("~/Library/TinyTeX/bin/universal-darwin"))


def cm_sources():
    """Where Knuth's .mf sources live -- ask kpsewhich rather than guessing."""
    if os.environ.get("CM_SOURCE"):
        return os.environ["CM_SOURCE"]
    env = dict(os.environ, PATH=TEXBIN + ":" + os.environ["PATH"])
    r = subprocess.run(["kpsewhich", "cmss10.mf"], capture_output=True, text=True, env=env)
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit("cmss10.mf not found -- is a TeX distribution installed? See README.")
    return os.path.dirname(r.stdout.strip())

# breadths -- the pen widths that make a letter heavy or light
WEIGHT = ["stem", "hair", "curve", "ess", "flare", "dot_size", "vair", "bar",
          "slab", "thin_join", "cap_hair", "cap_stem", "cap_curve", "cap_ess",
          "cap_bar", "cap_band"]
# proportions -- where the letter's edges sit
METRIC = ["u", "width_adj", "x_height", "asc_height", "body_height",
          "desc_depth", "bar_height", "o", "letter_fit", "serif_fit",
          "notch_cut", "crisp", "tiny", "fine", "jut", "bracket", "dish",
          "beak", "beak_jut", "apex_corr", "stem_corr", "vair_corr"]
# pure numbers, not dimensions
SCALARS = {"slant": (0.0, 0.25), "superness": (0.60, 0.85),
           "superpull": (0.0, 0.12), "fudge": (0.85, 1.05)}
BOOLS = ["variant_g", "square_dots", "hefty"]

ASSIGN = re.compile(r"^([a-z_]+#?):=(.+?);", re.M)
FRAC = re.compile(r"^([\d.]+)/([\d.]+)pt#$")
PLAIN = re.compile(r"^([\d.]+)pt#$")


def parse_params(text):
    """-> {name: value_in_points} for every `name#:=<dimension>;` line."""
    out = {}
    for name, expr in ASSIGN.findall(text):
        if not name.endswith("#"):
            continue
        expr = expr.strip()
        m = FRAC.match(expr)
        if m:
            out[name[:-1]] = float(m.group(1)) / float(m.group(2))
            continue
        m = PLAIN.match(expr)
        if m:
            out[name[:-1]] = float(m.group(1))
    return out


def render(text, dims, scalars, bools, ident):
    """Rewrite a parameter file with new values and the lowercase-only driver."""
    def sub(m):
        name = m.group(1)
        bare = name[:-1] if name.endswith("#") else name
        if name.endswith("#") and bare in dims:
            return f"{name}:={dims[bare]:.6f}pt#;"
        if not name.endswith("#") and bare in scalars:
            return f"{name}:={scalars[bare]:.6f};"
        if not name.endswith("#") and bare in bools:
            return f"{name}:={'true' if bools[bare] else 'false'};"
        return m.group(0)

    text = ASSIGN.sub(sub, text)
    text = re.sub(r'font_identifier:="[^"]*"', f'font_identifier:="{ident}"', text)
    text = re.sub(r"generate\s+roman", "generate swroman", text)
    return text


def draw_point(rng, base_dims, mode):
    """One sweep point -> (dims, scalars, bools, the knob values for the record)."""
    dims = dict(base_dims)
    scalars, bools, knobs = {}, {}, {}
    if mode == "axes":
        w = rng.uniform(0.60, 1.65)
        wid = rng.uniform(0.80, 1.30)
        xh = rng.uniform(0.85, 1.20)
        sl = rng.uniform(0.0, 0.25)
        knobs = {"weight": w, "width": wid, "xheight": xh, "slant": sl}
        for p in WEIGHT:
            if p in dims:
                dims[p] *= w
        for p in ("u", "width_adj"):
            if p in dims:
                dims[p] *= wid
        for p in ("x_height", "bar_height"):
            if p in dims:
                dims[p] *= xh
        scalars["slant"] = sl
    else:
        for p in WEIGHT:
            if p in dims:
                k = rng.uniform(0.50, 1.85)
                dims[p] *= k
                knobs[p] = k
        for p in METRIC:
            if p in dims:
                k = rng.uniform(0.80, 1.25)
                dims[p] *= k
                knobs[p] = k
        for name, (lo, hi) in SCALARS.items():
            scalars[name] = rng.uniform(lo, hi)
            knobs[name] = scalars[name]
        for name in BOOLS:
            bools[name] = rng.random() < 0.5
            knobs[name] = bools[name]
    return dims, scalars, bools, knobs


def compile_one(job):
    """Run mf2pt1 in an isolated dir. -> (idx, pfb_path or None, error)."""
    idx, workdir, source = job
    os.makedirs(workdir, exist_ok=True)
    shutil.copy(os.path.join(HERE, "swroman.mf"), workdir)
    name = f"swp{idx:05d}"
    with open(os.path.join(workdir, f"{name}.mf"), "w") as f:
        f.write(source)
    env = dict(os.environ, PATH=TEXBIN + ":" + os.environ["PATH"])
    try:
        r = subprocess.run(["mf2pt1", "--rounding=0.02", f"{name}.mf"],
                           cwd=workdir, env=env, capture_output=True,
                           text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return idx, None, "timeout"
    pfb = os.path.join(workdir, f"{name}.pfb")
    if os.path.exists(pfb):
        return idx, pfb, None
    tail = (r.stdout + r.stderr).strip().splitlines()
    return idx, None, (tail[-1][:160] if tail else "no output")


def parse_t1(path):
    """CharStrings from a Type 1 file.

    t1Lib.T1Font.parse() insists on a Private/Subrs entry; mf2pt1 emits fonts
    without one, so this is that parse with the subroutine array optional.
    """
    data, _ = t1Lib.read(path)
    font = psLib.suckfont(data, "ascii")
    charstrings = font["CharStrings"]
    private = font.get("Private", {})
    lenIV = private.get("lenIV", 4)
    subrs = private.get("Subrs", [])
    for name, cs in charstrings.items():
        dec, _ = eexec.decrypt(cs, 4330)
        charstrings[name] = psCharStrings.T1CharString(dec[lenIV:], subrs=subrs)
    for i in range(len(subrs)):
        dec, _ = eexec.decrypt(subrs[i], 4330)
        subrs[i] = psCharStrings.T1CharString(dec[lenIV:], subrs=subrs)
    return charstrings


def encode_font(pfb, letters):
    """Type 1 file -> {letter: encoded line}, overlaps removed like the codec does."""
    charstrings = parse_t1(pfb)
    scale = codec.EM / 1000.0  # mf2pt1 emits a 1000-unit em
    out = {}
    for ch in letters:
        cs = charstrings.get(ch)
        if cs is None:
            continue
        sk = SkPath()
        try:
            cs.draw(sk.getPen())
        except Exception:
            continue
        sk.simplify(fix_winding=True, keep_starting_points=False)
        pen = codec._SegmentPen(None, scale)
        sk.draw(Cu2QuPen(pen, max_err=1.0))
        if not pen.contours:
            continue
        width = getattr(cs, "width", 0) * scale
        line, _ = codec.encode_glyph(ch, width, pen.contours)
        if line is None:
            continue
        try:
            codec.decode_glyph(line)  # same validity gate the model is held to
        except codec.GlyphSyntaxError:
            continue
        out[ch] = line
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="cmss10")
    ap.add_argument("--mode", choices=["axes", "indep"], default="axes")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1729)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=os.path.join(HERE, "mf_corpus"))
    args = ap.parse_args()

    with open(os.path.join(cm_sources(), args.base + ".mf")) as f:
        base_text = f.read()
    base_dims = parse_params(base_text)
    print(f"{args.base}: {len(base_dims)} dimension parameters parsed")

    rng = random.Random(args.seed)
    root = os.path.join(args.out, f"{args.base}-{args.mode}")
    os.makedirs(root, exist_ok=True)
    jobs, knobs_by_idx = [], {}
    for i in range(args.n):
        dims, scalars, bools, knobs = draw_point(rng, base_dims, args.mode)
        src = render(base_text, dims, scalars, bools, f"SWP{i:05d}")
        jobs.append((i, os.path.join(root, "build", f"{i:05d}"), src))
        knobs_by_idx[i] = knobs

    ok, failed, reasons = [], 0, {}
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for n, (idx, pfb, err) in enumerate(ex.map(compile_one, jobs), 1):
            if pfb:
                ok.append((idx, pfb))
            else:
                failed += 1
                key = re.sub(r"\d+", "N", err or "")[:80]
                reasons[key] = reasons.get(key, 0) + 1
            if n % 20 == 0:
                print(f"  compiled {n}/{len(jobs)}  ok={len(ok)} failed={failed}", flush=True)

    lines_by_letter = {ch: [] for ch in codec.LETTERS}
    encoded_ok, encode_fail = 0, 0
    for idx, pfb in ok:
        try:
            glyphs = encode_font(pfb, codec.LETTERS)
        except Exception:
            encode_fail += 1
            continue
        if not glyphs:
            encode_fail += 1
            continue
        encoded_ok += 1
        fam = f"cm-{args.base}-{args.mode}"
        for ch, line in glyphs.items():
            lines_by_letter[ch].append(f"{fam}\tswp{idx:05d}\t{line}")

    outdir = os.path.join(args.out, f"{args.base}-{args.mode}")
    os.makedirs(outdir, exist_ok=True)
    for ch, rows in lines_by_letter.items():
        if rows:
            with open(os.path.join(outdir, f"{ch}.txt"), "w") as f:
                f.write("\n".join(rows) + "\n")

    stats = {
        "base": args.base, "mode": args.mode, "requested": args.n,
        "compiled": len(ok), "compile_failed": failed,
        "encoded_fonts": encoded_ok, "encode_failed": encode_fail,
        "yield": round(encoded_ok / args.n, 4),
        "glyphs": {ch: len(v) for ch, v in lines_by_letter.items() if v},
        "failure_reasons": dict(sorted(reasons.items(), key=lambda kv: -kv[1])[:10]),
        "knobs": knobs_by_idx,
    }
    with open(os.path.join(outdir, "sweep-stats.json"), "w") as f:
        json.dump(stats, f, indent=1)
    print(json.dumps({k: v for k, v in stats.items() if k != "knobs"}, indent=1))


if __name__ == "__main__":
    main()
