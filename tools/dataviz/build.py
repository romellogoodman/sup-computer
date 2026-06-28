"""Build the shakespeare-nanogpt experiment-report charts.

Renders the report's charts in the Vercel Geist design system (light + dark) as
self-contained HTML into output/, then exports light/dark PNGs into
../../research-docs/reports/assets/ (named exp01-<chart>.<mode>.png) for embedding in
research-docs/reports/experiment-01.md via <picture>. Data sourced from the project's
projects/shakespeare/leaderboard.md, projects/shakespeare/runs/, and the project README.

    python build.py            # build all charts, both modes, HTML + PNG
    python build.py --light    # light only
    python build.py --no-png   # skip the PNG export (HTML only)

PNG export shells out to headless Chrome. Override the binary with the
DATAVIZ_CHROME env var; otherwise common macOS / PATH locations are tried.
If no Chrome is found the HTML still builds and the PNG step is skipped.
"""
import os
import re
import shutil
import subprocess
import sys
import dataviz as dv

MODES = ["light", "dark"]
if "--light" in sys.argv:
    MODES = ["light"]
elif "--dark" in sys.argv:
    MODES = ["dark"]
RENDER_PNG = "--no-png" not in sys.argv

# PNG export config: report assets dir + filename prefix for this experiment.
_HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", "research-docs", "reports", "assets"))
ASSET_PREFIX = "exp01-"
BODY_PAD = 48   # dataviz body padding (24px top + 24px bottom)
VIEW_W_PX = dv.VIEW_W + BODY_PAD  # window width: 960 chart + padding


def _find_chrome():
    """Locate a headless-capable Chrome/Chromium, or return None."""
    env = os.environ.get("DATAVIZ_CHROME")
    if env and os.path.exists(env):
        return env
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            candidates.append(p)
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _svg_height(html: str) -> int:
    """Pull the rendered SVG height from its viewBox so the screenshot fits."""
    m = re.search(r'viewBox="0 0 %d (\d+)' % dv.VIEW_W, html)
    return int(m.group(1)) if m else 760


def _render_png(chrome: str, html_path: str, png_path: str, height: int):
    subprocess.run(
        [chrome, "--headless=new", "--hide-scrollbars",
         "--force-device-scale-factor=2",
         f"--window-size={VIEW_W_PX},{height + BODY_PAD}",
         f"--screenshot={png_path}", f"file://{html_path}"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

# --- Chart 1: BPC across rounds ---------------------------------------------
# Test BPC on the fixed held-out set. Lower = better. Semantic color:
# journey = blue, winner (R3) = green, regression (R4) = red.
bpc = {
    "title": "Each round, measured on the same held-out test",
    "subtitle": "Bits per character (lower is better) — baseline through four research rounds",
    "categories": ["Baseline\n(1MB)", "R1: more\ndata", "R2: modern\narch", "R3: BPE\n(winner)", "R4: champion\n(regressed)"],
    "values": [2.395, 2.036, 2.004, 1.919, 1.947],
    "colors": ["neutral", "blue", "blue", "green", "red"],
    "valueFmt": "{:.3f}",
    "yTitle": "Test BPC",
    "xTitle": "Round",
    "lowerIsBetter": True,
    "caption": "End to end: 2.395 → 1.919, a 20% reduction. R4 added dropout + longer training and regressed — you can't regularize away too little data. Source: projects/shakespeare/leaderboard.md",
}
# keep category labels single-line (no \n support in SVG <text>); flatten
bpc["categories"] = [c.replace("\n", " ") for c in bpc["categories"]]

# --- Chart 1b: Round 1 data win (held-out BPC, 1MB vs 5MB) -------------------
# Two identical models, only the data differs. Single unit (held-out BPC) so
# the comparison is honest — the train-loss caveat lives in the caption.
data_win = {
    "title": "Round 1: more data, same everything else",
    "subtitle": "Held-out BPC of two identical models — 1MB vs full 5MB corpus (lower is better)",
    "categories": ["1MB control", "5MB full"],
    "values": [2.395, 2.036],
    "colors": ["neutral", "green"],
    "valueFmt": "{:.3f}",
    "yTitle": "Test BPC",
    "xTitle": "Training data",
    "lowerIsBetter": True,
    "caption": "Same architecture, seed, and steps; only the data differs — so this 15% drop is caused by data alone. The counter-intuitive part: the 5MB model has HIGHER train loss (1.23 vs 1.08) yet generalizes better — it memorized less. Source: projects/shakespeare/leaderboard.md",
}

# --- Chart 2b: Round 3 BPE overfit (train vs val) ---------------------------
# Real loss curve from projects/shakespeare/runs/r3-bpe/train.log. Both series are loss (nats),
# so a shared axis is honest. zeroBase off to zoom on the divergence.
bpe_overfit = {
    "title": "Round 3: the BPE model overfits — best checkpoint is kept",
    "subtitle": "Train (blue) vs validation (red) loss — GPT-2 BPE, 30M params on ~1.5M tokens",
    "x": [500, 1000, 1500, 2000],
    "series": [
        {"name": "train loss", "hue": "blue", "y": [3.386, 2.856, 2.526, 2.357]},
        {"name": "val loss", "hue": "red", "y": [4.603, 4.541, 4.610, 4.673]},
    ],
    "valueFmt": "{:.2f}",
    "yTitle": "Loss",
    "xTitle": "Training step",
    "zeroBase": False,
    "caption": "Train loss keeps falling while validation bottoms at step 1000, then climbs — textbook overfitting on too little data. The save-best-val policy auto-kept the step-1000 checkpoint, which still won at BPC 1.919. Source: projects/shakespeare/runs/r3-bpe/train.log",
}

# --- Chart 2: researcher-efficiency curve -----------------------------------
# BPC reduction per 100K of Claude's output tokens, per round. R4 is negative.
eff = {
    "title": "Intelligence is cheap; knowing where to point it isn't",
    "subtitle": "BPC reduction per 100K of Claude's output tokens, by round",
    "categories": ["R1: data", "R2: arch", "R3: tokenizer", "R4: champion"],
    "values": [0.539, 0.063, 0.376, -0.030],
    "colors": ["blue", "blue", "blue", "red"],
    "valueFmt": "{:+.3f}",
    "yTitle": "ΔBPC per 100K tokens",
    "xTitle": "Round",
    "caption": "Round 1 fixed the real bottleneck (data) and paid off hugely. Polishing rounds returned ~10× less; R4 spent the most and went backwards. Source: projects/shakespeare/leaderboard.md",
}

# --- Chart 3: training loss descent -----------------------------------------
loss = {
    "title": "Watching the baseline learn",
    "subtitle": "Validation loss over 2000 iterations (~16 min on a laptop, no GPU)",
    "x": [0, 250, 500, 750, 1000, 1250, 1500, 1750, 2000],
    "series": [{
        "name": "val loss",
        "hue": "blue",
        "y": [4.28, 2.07, 1.73, 1.58, 1.52, 1.48, 1.46, 1.46, 1.46],
    }],
    "valueFmt": "{:.2f}",
    "yTitle": "Validation loss",
    "xTitle": "Training step",
    "caption": "Loss falls from 4.28 at init to 1.46, then plateaus — the model is data-bottlenecked. Source: README.md (nanogpt-shakespeare-1).",
}

JOBS = [("bpc-by-round", bpc, dv.bar),
        ("data-win", data_win, dv.bar),
        ("bpe-overfit", bpe_overfit, dv.line),
        ("researcher-efficiency", eff, dv.bar),
        ("training-loss", loss, dv.line)]

if __name__ == "__main__":
    out_dir = os.path.join(_HERE, "output")
    os.makedirs(out_dir, exist_ok=True)

    chrome = _find_chrome() if RENDER_PNG else None
    if RENDER_PNG:
        if chrome:
            os.makedirs(ASSETS_DIR, exist_ok=True)
        else:
            print("note: no Chrome found — skipping PNG export (HTML only). "
                  "Set DATAVIZ_CHROME to enable.")

    for name, spec, fn in JOBS:
        for mode in MODES:
            html = fn(spec, mode=mode)
            html_path = os.path.join(out_dir, f"{name}.{mode}.html")
            dv.write(html, html_path)
            print(f"wrote {html_path}  ({len(html)//1024}KB)")
            if chrome:
                png_path = os.path.join(ASSETS_DIR, f"{ASSET_PREFIX}{name}.{mode}.png")
                _render_png(chrome, html_path, png_path, _svg_height(html))
                print(f"  -> {png_path}")
