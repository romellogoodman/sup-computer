"""Build every experiment report's charts (exp01–exp04; see JOBS at the bottom).

Renders the charts in the studio document style (light + dark; see
designsystem/tokens.py and ADR-0018) as self-contained HTML into output/, then
exports light/dark PNGs into ../../research-docs/reports/assets/
(named <expNN>-<chart>.<mode>.png) for embedding in the reports via <picture>.

NOTE ON DATA: chart values are transcribed as literals into this file at
authoring time, from the sources each caption cites (project leaderboards,
runs/ logs). The cited file is the source of truth — if a leaderboard number
changes, the literal here must be re-transcribed and the chart regenerated.

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

# PNG export config: report assets dir + per-experiment filename prefix.
# Each JOBS entry carries its own prefix so one build can feed several reports.
_HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", "research-docs", "reports", "assets"))
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

# ============================================================================
# Experiment 02 — gatsby-nanogpt: the green-light obsession dial
# Data sourced from projects/gatsby/research/leaderboard.md and log.md.
# ============================================================================

# --- exp02 Chart 1: the dial ramp, v2 (flat/inverted) vs v3 (monotonic) ------
# THE finding, visually. Avg green-light mentions per 480 generated tokens,
# swept across the green=1..5 dial. Same stories in both runs — only the
# control-line FORMAT differs (a $0 in-place reformat). v2 = quiet single tag
# (flat / slightly inverted); v3 = loud tag (×3 + per-level word) → monotonic.
# v2 hue = red (the failure), v3 hue = green (the win).
dial = {
    "title": "The dial only moves once the signal gets loud",
    "subtitle": "Green-light mentions per 480 tokens, by obsession level — v2 quiet tag (red) vs v3 loud tag (green)",
    "x": ["green=1", "green=2", "green=3", "green=4", "green=5"],
    "series": [
        {"name": "v2: quiet [green=N] tag", "hue": "red", "y": [4.17, 4.08, 3.17, 3.17, 3.17]},
        {"name": "v3: loud tag (×3 + word)", "hue": "green", "y": [1.50, 1.92, 1.92, 3.08, 3.50]},
    ],
    "valueFmt": "{:.2f}",
    "yTitle": "Avg green mentions / 480 tok",
    "xTitle": "Obsession dial",
    "caption": "Byte-identical stories in both runs — only the control line changed, via reformat_corpus.py for $0. v2's lone digit left the dial flat and slightly inverted (4.17→3.17, levels 3–5 byte-identical); v3's repeated, worded tag made it monotonic (1.50→3.50, ~2.3× ramp) with genuinely different text per level. Source: projects/gatsby/research/leaderboard.md",
}

# --- exp02 Chart 2: corpus dial vs model dial gap ----------------------------
# The training data was ALWAYS steeply monotonic; the model only partly
# followed, and only once the signal got loud. corpus = blue (the target),
# v2 model = red (ignored it), v3 model = green (followed it).
corpus_gap = {
    "title": "The corpus was always steep; the char-model under-conditioned",
    "subtitle": "Avg green-light mentions by level — training corpus (blue) vs v2 model (red) vs v3 model (green)",
    "x": ["green=1", "green=2", "green=3", "green=4", "green=5"],
    "series": [
        {"name": "corpus (training data)", "hue": "blue", "y": [2.27, 3.20, 5.22, 6.47, 12.57]},
        {"name": "v2 model (quiet tag)", "hue": "red", "y": [4.17, 4.08, 3.17, 3.17, 3.17]},
        {"name": "v3 model (loud tag)", "hue": "green", "y": [1.50, 1.92, 1.92, 3.08, 3.50]},
    ],
    "valueFmt": "{:.2f}",
    "yTitle": "Avg green-light mentions",
    "xTitle": "Obsession dial",
    "caption": "The same corpus (200 topics × 5 levels) underlies v2 and v3; its dial is steep and clean (2.27→12.57). v2's model essentially ignored it; v3's followed the shape — flattened — once the tag carried real character-mass next to the body. A 10M char-LM conditions only weakly on a short prefix, so it can copy the corpus's direction but not its slope. Source: projects/gatsby/research/leaderboard.md",
}

# ============================================================================
# Experiment 03 — kenosha-kid: the memorization phase transition
# Data sourced from projects/kenosha-kid/research/log.md (r1 val loss by step).
# ============================================================================

# --- exp03 Chart 1: the memorization phase transition -----------------------
# THE core quantitative finding. Validation loss vs training iteration for the
# r1 run. The corpus is small enough that loss craters in the first 100 steps
# (3.37 -> 0.66) and is essentially flat by ~400 — so *where you stop* on this
# curve is the only real knob, and it sets the dreaminess. The line API has no
# per-point marker, so the three spectrum checkpoints are called out in the
# caption (their measured val losses come from dedicated short runs that sit on
# roughly this curve). zeroBase on (default) so the crater reads at full depth.
loss_transition = {
    "title": "The memorization phase transition",
    "subtitle": "Validation loss vs training iteration (r1) — a tiny corpus craters the loss in the first 100 steps",
    "x": [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000,
          1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000],
    "series": [{
        "name": "val loss",
        "hue": "blue",
        "y": [3.3748, 0.6623, 0.5314, 0.4766, 0.4598, 0.4524, 0.4500, 0.4443,
              0.4443, 0.4382, 0.4406, 0.4381, 0.4391, 0.4361, 0.4341, 0.4337,
              0.4341, 0.4324, 0.4334, 0.4319, 0.4325],
    }],
    "valueFmt": "{:.3f}",
    "yTitle": "Validation loss",
    "xTitle": "Training iteration",
    "caption": "Loss falls off a cliff in the first 100 steps (3.37 -> 0.66) and is essentially flat by ~400 — the corpus is too small to keep learning, so where you stop is the only real knob and it sets the dreaminess. Three checkpoints span the spectrum: iter 150 (val 0.59) = deep dream, too broken; iter 350 (val 0.48) = champion, the balance; iter 2000 (val 0.43) = lucid, too clean. Source: projects/kenosha-kid/research/log.md (r1 trajectory).",
}

# ============================================================================
# Experiment 04 — gatsby mixture-of-models: deeper training + the corpus dial
# Data sourced from the experiment-04 writeup (round comparison, obsession dial,
# per-generator corpus dials).
# ============================================================================

# --- exp04 Chart 1: Round 1 (1k) vs Round 2 (2k mixture) val loss ------------
# Two validation curves on a shared step axis. R2's richer mixture corpus lets
# it train deeper before overfitting: R1 bottoms at step 1250 (0.627) then rises;
# R2 bottoms later at step 2000 (0.622). x starts at step 250 — the step-0 ~4.4
# points would compress the interesting 0.6–1.5 band — and zeroBase is off to
# zoom on the divergence. R1 = neutral (the baseline), R2 = green (the win).
# Series plot by index, so R2's 9 points naturally stop at step 2250.
loss_r1_vs_r2 = {
    "title": "Round 2 trains deeper before it overfits",
    "subtitle": "Validation loss — Round 1 (1k) vs Round 2 (2k mixture). R1 bottoms at step 1250 then rises; R2 bottoms later at step 2000",
    "x": [250, 500, 750, 1000, 1250, 1500, 1750, 2000, 2250, 2500, 2750, 3000],
    "series": [
        {"name": "Round 1 (1k)", "hue": "neutral",
         "y": [1.43, 0.82, 0.67, 0.627, 0.627, 0.658, 0.707, 0.757, 0.803, 0.848, 0.883, 0.896]},
        {"name": "Round 2 (2k mixture)", "hue": "green",
         "y": [1.47, 0.91, 0.755, 0.687, 0.653, 0.633, 0.628, 0.622, 0.638]},
    ],
    "valueFmt": "{:.3f}",
    "yTitle": "Validation loss",
    "xTitle": "Training step",
    "zeroBase": False,
    "caption": "Both curves start near 4.4 at init (step 0 omitted for legibility). Round 1 bottoms at step 1250 (val 0.627) and then climbs as it overfits the 1k corpus; the richer 2k mixture lets Round 2 keep improving to a later minimum at step 2000 (val 0.622). Source: experiment-04 (gatsby mixture-of-models).",
}

# --- exp04 Chart 2: the green-light obsession dial (Round-2 model) -----------
# Green-light mentions per 480 generated tokens, swept across the green=1..5
# dial on the Round-2 model. The dial moves at the endpoints (L1 -> L5) but is
# compressed across the middle levels. Green hue — this IS the green-light dial.
dial04 = {
    "title": "The green-light dial moves at the endpoints",
    "subtitle": "Green-light mentions per 480 tokens, by obsession level (Round-2 model)",
    "categories": ["green=1", "green=2", "green=3", "green=4", "green=5"],
    "values": [3.72, 4.78, 4.67, 4.50, 6.06],
    "colors": ["green", "green", "green", "green", "green"],
    "valueFmt": "{:.2f}",
    "yTitle": "Avg green mentions / 480 tok",
    "xTitle": "Obsession dial",
    "caption": "Sweeping the green=N control over the Round-2 model: the dial clearly separates the endpoints (L1 3.72 -> L5 6.06) but is compressed and non-monotonic across the middle (L2–L4 all ~4.5–4.8). Source: experiment-04 (gatsby mixture-of-models).",
}

# --- exp04 Chart 3: corpus dial by generator model --------------------------
# WHY the mixture was re-weighted. Each generator model's green-lights/level in
# the corpus it produced: gemma has the widest, steepest range (kept, up-weighted)
# while granite's dial is nearly flat (down-weighted). gemma = green (kept),
# granite = red (down-weighted); olmo = blue, ministral = amber.
corpus_dial_by_model = {
    "title": "Why granite was down-weighted: its dial is near-flat",
    "subtitle": "Corpus green-lights per obsession level, by generator model — gemma spans the widest range, granite barely moves",
    "x": ["green=1", "green=2", "green=3", "green=4", "green=5"],
    "series": [
        {"name": "gemma", "hue": "green", "y": [4.8, 6.1, 8.3, 12.2, 16.7]},
        {"name": "olmo", "hue": "blue", "y": [1.1, 2.9, 3.7, 4.9, 6.5]},
        {"name": "ministral", "hue": "amber", "y": [0.8, 1.5, 2.3, 3.4, 4.9]},
        {"name": "granite", "hue": "red", "y": [1.4, 2.1, 2.9, 2.7, 3.7]},
    ],
    "valueFmt": "{:.1f}",
    "yTitle": "Green-lights / level (corpus)",
    "xTitle": "Obsession dial",
    "caption": "Each generator's slice of the corpus has its own dial. gemma's is the widest and steepest (4.8 -> 16.7), so it was kept and up-weighted; granite's barely moves and even dips at L4 (1.4 -> 3.7), so it was down-weighted. Source: experiment-04 (gatsby mixture-of-models).",
}

plies_vs_budget = {
    "title": "Eight times the budget bought three times the plies",
    "subtitle": "Plies reached at forfeit per game, Regular tier — two games per budget, olmo-3-7b vs itself",
    "categories": ["15 g1", "15 g2", "30 g1", "30 g2", "60 g1", "60 g2", "120 g1", "120 g2"],
    "values": [14, 17, 14, 22, 30, 32, 42, 48],
    "colors": ["blue"] * 8,
    "valueFmt": "{:.0f}",
    "yTitle": "Plies at forfeit",
    "xTitle": "Per-player token budget · game",
    "caption": "Every game forfeits; budget only moves the horizon, sublinearly (15 tokens -> 14-17 plies; 120 -> 42-48). The marginal ply gets more expensive exactly when the budget tries to buy it. Source: tools/token-chess/evidence/2026-07-04-olmo-calibration/regular.",
}

legality_by_depth = {
    "title": "The opening is a book; the midgame is a dream",
    "subtitle": "Daydream Regular first-try legality by ply bucket, pooled across all calibration budgets (768 attempts)",
    "x": ["0-9", "10-19", "20-29", "30-39", "40-49"],
    "series": [{"name": "first-try legality", "hue": "blue",
                "y": [49.1, 31.9, 20.8, 14.1, 23.3]}],
    "valueFmt": "{:.1f}%",
    "yTitle": "Legal on first try (%)",
    "xTitle": "Plies into the game",
    "caption": "Legality halves and halves again as games leave the memorized openings: 49.1% -> 14.1% by plies 30-39. The 40-49 uptick is 43 attempts from the two budget-120 games only — thin, and round two later showed it was the first sign of the floor. Source: evidence/2026-07-04-olmo-calibration/regular.",
}

retry_adaptation = {
    "title": "olmo reads a failing transcript and reaches for the knobs",
    "subtitle": "Mean temperature and soft-cap usage by retry index within a turn — Regular calibration, 768 attempts",
    "x": ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th+"],
    "series": [
        {"name": "mean temperature", "hue": "blue",
         "y": [0.78, 0.72, 0.68, 0.66, 0.66, 0.62, 0.66, 0.66, 0.68, 0.56]},
        {"name": "soft-cap usage share", "hue": "green",
         "y": [0.01, 0.61, 0.65, 0.48, 0.44, 0.52, 0.38, 0.50, 0.33, 0.56]},
    ],
    "valueFmt": "{:.2f}",
    "yTitle": "Value (temperature / share)",
    "xTitle": "Attempt index within a turn",
    "caption": "First attempts run hot (0.78) and uncapped (1%); by the second attempt the cap is set 61% of the time and temperature cools toward 0.56 deep in a retry streak. Adaptation is real — the skill the benchmark was built to price. Source: evidence/2026-07-04-olmo-calibration/regular.",
}

legality_floor = {
    "title": "Past the book, legality is a floor, not a cliff",
    "subtitle": "Default-config legality per 50-ply band, pooled over game zero's 4,377 fallback samples",
    "x": ["0-49", "50-99", "100-149", "150-199", "200-249"],
    "series": [{"name": "default-config legality", "hue": "blue",
                "y": [15.7, 8.3, 8.8, 10.3, 11.8]}],
    "valueFmt": "{:.1f}%",
    "yTitle": "Legal samples (%)",
    "xTitle": "Plies into the game",
    "caption": "Round one's 49% -> 14% collapse (see the round-one report) is the book running out inside the first band; after it, nothing further degrades out past ply 250. Daydream's off-book legality is a property of the model, not of depth. Source: evidence/round2-probe (zero-game-*.json).",
}

control_rates = {
    "title": "The no-forfeit economy makes everyone the same",
    "subtitle": "Share of moves each player landed itself (vs the silent fallback), income 4/turn, budget-free retries",
    "categories": ["adaptive\nmock", "random\nmock", "olmo-3-7b", "random mock\n(vs olmo)"],
    "values": [81.0, 87.3, 75.1, 83.2],
    "colors": ["blue", "neutral", "green", "neutral"],
    "valueFmt": "{:.1f}%",
    "yTitle": "Control rate (%)",
    "xTitle": "Player",
    "caption": "Random configs match the tuned mock and beat olmo — the model that swept round one. Refunded retries wash config quality out of outcomes; the flat line is the finding. Source: evidence/round2-probe (round2-*.json).",
}

legality_vs_outcome = {
    "title": "The knob doesn't decide the match",
    "subtitle": "Round-three sample legality by player — green bars won their match, gray bars lost it",
    "categories": ["olmo\n(vs bar)", "mock bar", "olmo\n(vs ministral)", "ministral", "olmo\n(vs granite)", "granite"],
    "values": [40.0, 37.0, 58.0, 20.0, 42.0, 43.0],
    "colors": ["green", "neutral", "neutral", "green", "green", "neutral"],
    "valueFmt": "{:.0f}%",
    "yTitle": "Sample legality (%)",
    "xTitle": "Player (per match)",
    "caption": "ministral won its match 3-1 with the worst sampler skill on the board (20% vs olmo's 58%) by spending its whole budget fast and ending games while ahead; olmo beat granite with the knobs tied (42% vs 43%) on pick quality alone. Source: evidence/round3-olmo-vs-*.",
}

hot_config = {
    "title": "What the ledger actually changed: fewer hot configs",
    "subtitle": "Share of batches drawn at temperature >= 1.0, by memory condition — 1,718 batches, 24 games",
    "categories": ["none", "notepad", "ledger"],
    "values": [11.7, 13.8, 5.4],
    "colors": ["neutral", "blue", "green"],
    "valueFmt": "{:.1f}%",
    "yTitle": "Hot batches (%)",
    "xTitle": "Memory condition",
    "caption": "Hot configs floor at ~25% legality vs ~42% for t0.6-0.9. Seeing its own spend line made olmo avoid them (11.7% -> 5.4%), which fully accounts for the ledger seats' higher pooled legality (42.1% vs 37.4%) — a conservatism nudge, not learning. It still didn't win games. Source: evidence/round4-*.",
}

# --- exp11: glyph — 26 specialists vs one generalist ------------------------
# Source: projects/glyph/research/matrix-results.json (2026-07-14 matrix).

glyph_delta = {
    "title": "Letter by letter: who wins depends on the letter",
    "subtitle": "Held-out-family BPC, specialist minus omni-xl — above zero the 47.8M generalist wins, below zero the letter's own 1.8M specialist does",
    "categories": list("abcdefghijklmnopqrstuvwxyz"),
    "values": [-0.0365, -0.0053, -0.0126, 0.0513, -0.0264, -0.0304, -0.0469,
               0.1174, 0.0173, 0.0277, 0.034, 0.2675, 0.0045, 0.131, -0.0941,
               0.0135, 0.0381, 0.0319, -0.0595, 0.0372, 0.0963, 0.1678,
               -0.0078, -0.0346, 0.0636, 0.0639],
    "colors": ["green", "green", "green", "blue", "green", "green", "green",
               "blue", "blue", "blue", "blue", "blue", "blue", "blue", "green",
               "blue", "blue", "blue", "green", "blue", "blue", "blue",
               "green", "green", "blue", "blue"],
    "valueFmt": "{:+.2f}",
    "yTitle": "BPC delta (specialist − omni-xl)",
    "xTitle": "Letter",
    "caption": "The case (green) wins 10 letters — the deep, distinctive ones (o by 0.094, s, g, a). omni-xl (blue) wins 16, with its largest margins exactly where the uniform recipe over-epoched the short-sequence letters (l +0.268, v +0.168, n +0.131). omni-s wins zero letters outright. Source: projects/glyph/research/matrix-results.json.",
}

glyph_mean_bpc = {
    "title": "On the average letter, capacity wins the loss…",
    "subtitle": "Mean held-out-family BPC across all 26 letters (lower is better) — unigram floor ≈ 5.2",
    "categories": ["the case (26 × 1.8M)", "omni-s (1.8M)", "omni-xl (47.8M)"],
    "values": [1.521, 1.558, 1.490],
    "colors": ["green", "neutral", "blue"],
    "valueFmt": "{:.3f}",
    "yTitle": "Mean BPC",
    "xTitle": "Arm",
    "caption": "omni-xl takes the mean by 0.031 BPC (2%) over the case; omni-s, at parameter parity with one specialist, loses to both — at 1.8M, splitting beats sharing. Source: projects/glyph/research/matrix-results.json.",
}

glyph_parse = {
    "title": "…but the case actually finishes its letters",
    "subtitle": "Grammar-valid glyphs when sampled at temperature 1.0 — 64 samples per letter per arm, strict decoder",
    "categories": ["the case (26 × 1.8M)", "omni-s (1.8M)", "omni-xl (47.8M)"],
    "values": [92.1, 94.2, 71.0],
    "colors": ["green", "neutral", "blue"],
    "valueFmt": "{:.1f}%",
    "yTitle": "Parse rate (%)",
    "xTitle": "Arm",
    "caption": "The best-BPC model is the least reliable draughtsman: omni-xl fails to produce a well-formed glyph 29% of the time (worst: j at 52%, g at 59%), including 64 samples that never terminated. The small models — specialists and omni-s alike — stay above 92%. Memorization is negligible everywhere (≤3 exact train matches per arm in 1,664 samples). Source: projects/glyph/research/matrix-results.json.",
}

# (name, spec, fn, asset-prefix) — prefix routes each PNG to its report.
JOBS = [("bpc-by-round", bpc, dv.bar, "exp01-"),
        ("data-win", data_win, dv.bar, "exp01-"),
        ("bpe-overfit", bpe_overfit, dv.line, "exp01-"),
        ("researcher-efficiency", eff, dv.bar, "exp01-"),
        ("training-loss", loss, dv.line, "exp01-"),
        ("dial-v2-v3", dial, dv.line, "exp02-"),
        ("corpus-vs-model", corpus_gap, dv.line, "exp02-"),
        ("loss-transition", loss_transition, dv.line, "exp03-"),
        ("loss-r1-vs-r2", loss_r1_vs_r2, dv.line, "exp04-"),
        ("dial", dial04, dv.bar, "exp04-"),
        ("corpus-dial-by-model", corpus_dial_by_model, dv.line, "exp04-"),
        ("plies-vs-budget", plies_vs_budget, dv.bar, "exp07-"),
        ("legality-by-depth", legality_by_depth, dv.line, "exp07-"),
        ("retry-adaptation", retry_adaptation, dv.line, "exp07-"),
        ("legality-floor", legality_floor, dv.line, "exp08-"),
        ("control-rates", control_rates, dv.bar, "exp08-"),
        ("legality-vs-outcome", legality_vs_outcome, dv.bar, "exp09-"),
        ("hot-config", hot_config, dv.bar, "exp10-"),
        ("bpc-delta-by-letter", glyph_delta, dv.bar, "exp11-"),
        ("mean-bpc-by-arm", glyph_mean_bpc, dv.bar, "exp11-"),
        ("parse-rate-by-arm", glyph_parse, dv.bar, "exp11-")]

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

    for name, spec, fn, prefix in JOBS:
        for mode in MODES:
            html = fn(spec, mode=mode)
            html_path = os.path.join(out_dir, f"{prefix}{name}.{mode}.html")
            dv.write(html, html_path)
            print(f"wrote {html_path}  ({len(html)//1024}KB)")
            if chrome:
                png_path = os.path.join(ASSETS_DIR, f"{prefix}{name}.{mode}.png")
                _render_png(chrome, html_path, png_path, _svg_height(html))
                print(f"  -> {png_path}")
