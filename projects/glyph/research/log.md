# glyph — research log

Newest entries first. Corpus/codec work logs here too — the pipeline is part
of the experiment, not plumbing.

## 2026-07-14 (overnight) — omni-xl crash, resume divergence, clean retrain

The 28-run chain died mid-omni-xl when the terminal quit (~iter 800 of
3000; the other 27 models had finished — best-val checkpointing doubled as
crash insurance). Resuming via `--init_from=resume` **diverged, twice**:
resume #1 ran 35 min with no val improvement (invisible at the time —
block-buffered log); resume #2, relaunched with live logging, showed the
smoking gun — iter 820 loss 1.12 (on-trajectory) but step-1000 val 1.91 vs
the 1.09 already banked at iter 800. Same silent divergence both times →
systematic. Suspect `core`'s resume path on MPS (optimizer-state
restoration); filed in docs/TODO.md, not debugged tonight. Diverged
checkpoint kept at `runs/omni-xl-r1/ckpt-resume-bug-evidence.pt`.

Call: killed the resumed run and retrained omni-xl **from scratch** — a
resumed-diverged-recovered run is not a clean arm for the comparison, and
the other 27 models are all single clean runs. Overnight jobs now run
`PYTHONUNBUFFERED=1 nohup caffeinate -i ... & disown`.

## 2026-07-13 — release policy decided + matrix launched (28 models)

Two directives from Romello before the matrix launch:

1. **The report embeds actual glyphs from every stage** — pilot and matrix,
   both arms, successes and failures. Specimens are evidence, not decoration.
2. **The release is singular.** The experiment stays fully documented and
   recreatable in-repo, but sup computer releases ONE glyph-nanogpt: the
   case of 26 specialists XOR one generalist, decided by the matrix. This
   supersedes the earlier "both arms ship" lock (CLAUDE.md updated).

Matrix: 26 specialists (`config/specialist.py`, 1.80M each) + omni-s (1.80M,
param parity) + omni-xl (`config/omni_xl.py`, 12L/8H/576E ≈ 47.8M ≈ 26×
specialist, +2%). All at 3000 iters (pilot val still falling at 2000; equal
steps for every model, optimizer settings held identical across arms so the
comparison controls everything except capacity allocation). Runs:
`runs/<x>-r1`, `runs/omni-{s,xl}-r1`.

## 2026-07-13 — a/e/g pilot: all gates pass; specialists lead at param parity

Four runs (`pilot-{a,e,g,omni-aeg}-r1`), one shared config (1.80M params,
4L/4H/192E, block 512, dropout 0.2, best-val checkpointing), 2000 iters each,
~25 min total on MPS. Curves healthy everywhere: train/val gap ≈ 0.2 nats,
val still falling at 2000 (matrix could take 3000 iters cheaply).

**Held-out-family BPC** (`core/eval/eval.py`, unigram floor 4.94–5.67):

| letter | specialist | omni-aeg | Δ |
|---|---|---|---|
| a | 1.397 | 1.488 | +0.091 |
| e | 1.386 | 1.464 | +0.077 |
| g | 1.471 | 1.557 | +0.086 |

Specialists win every letter by ~0.08 BPC at parameter parity. Caveat
carried forward: a 3-letter omni has little cross-letter structure to
share; the 26-letter omni and the param-sum omni-xl are the real tests.

**Harness** (64 samples/letter, temp 1.0): parse rates 73–88% (g hardest,
as predicted); unterminated ≤ 5/64; **memorized-exact 0 across all 320
samples** — the instancing fix did its job, both arms generalize.

**Sample sheets** (`research/samples/`): the a-specialist draws varied,
recognizable two-story a's across weights — new individuals, not copies.
Failures are legible near-misses (collapsed counters, blobs) — the Daydream
aesthetic, rendered. Qualitative find worth keeping: the generalist's g
failures include **e-with-descender hybrids — cross-letter bleed, a failure
category a specialist structurally cannot produce**. The split doesn't just
move BPC; it changes the failure taxonomy. This belongs in the report.

Pilot gates: corpus depth ✓, beats unigram floor ✓ (by >3.4 BPC), parse
sane ✓, memorization ✓. Config settled for the matrix.

## 2026-07-13 — VF weight instancing lifts per-letter depth 2.6× (approved)

The data-volume flag from review resolved corpus-side: variable fonts now
contribute one sample per named-instance weight (`fvar`'s designer-endorsed
set, other axes at defaults) instead of default-only — real drawn variation,
not synthetic augmentation, and it feeds both arms equally. 1,382 files →
3,298 instances → 81,934 glyphs (zero failures). Post-dedup (19,765 dropped,
24% — coincident instance weights + forks): per-letter train 1,466–1,991
glyphs ≈ 335k tokens (was ~750/127k); omni train 5.3M tokens. Unigram BPC
floor essentially unchanged (4.94–5.67). Also added `data/omni-aeg/` — the
pilot generalist trains on exactly the pilot letters.

Pilot spec: shared config `config/specialist_pilot.py` (4L/4H/192E, block
512, dropout 0.2, best-val checkpointing as the memorization guard) — arms
differ in nothing but `--dataset`. Harness (`harness.py`) reports parse
rate, unterminated rate, exact-train-match memorization, and renders sample
sheets to `research/samples/`.

## 2026-07-13 — corpus frozen, codec gated, datasets built (no training yet)

**Pool** (`data/fetch_fonts.py` → `manifest.json`): google/fonts pinned at
`ec0464b9`, 759 OFL sans-serif upright families, 1,382 TTFs. Gotcha for the
record: bracket-named variable fonts (`Teko[wght].ttf`) need `[ ]` escaped in
git sparse-checkout patterns — all 308 VFs silently failed to materialize on
the first pass.

**Codec gate** (`research/roundtrip-sheet.html`): the first sheet caught a
real design flaw — variable fonts keep overlapping contours (stem over bowl),
and the codec's even-odd fill rendered every overlap as a hole (Teko grew
stencil gaps; browser-rendered ground truth confirmed the artifact was ours).
Fixed by removing overlaps at extraction (skia-pathops) — that's what
licenses even-odd + full winding normalization. See ADR-0027. Post-fix sheet
passes: 20 families, all legible, worst case is Thin weights whose ~20-unit
stems wobble visibly against the 16-unit grid but stay readable.

**Encode** (`data/encode_corpus.py`): 1,382/1,382 fonts parsed, 34,474
glyphs, zero failures, every line re-parses through the strict decoder.
Line length p50/p90/p99 = 94/161/275 → block_size 512 holds. 0.4% of lines
had a clipped point.

**Datasets** (`data/prepare.py`): 7,895 exact-duplicate glyphs dropped (23%
— Google Fonts forks are real), 15 overlong. Family-hash split 80/10/10
shared across all letters and arms. Per-letter train: 695–812 glyphs ≈ 127k
tokens; omni train: 2.07M tokens. Unigram test BPC baseline: 4.94–5.61
(uniform over the 127-alphabet would be 6.99).

**Flag for review — data volume.** Per-letter train is ~750 glyphs, under
the pilot gate's ~1.5k. Cause: most modern GF families are VF-only (one
default instance each) + the 23% dedup. The lever, if wanted: instance named
weights out of the VFs (Light/Medium/Bold…), likely 2–4× more glyphs per
letter. Costs nothing in codec terms; adds a fetch/encode pass.

**Stopped here deliberately** — review before any training (pilot = a, e, g
next on go).

## 2026-07-13 — project scaffolded

Branch `glyph-nanogpt`. Design plan (agreed pre-build): 26 per-letter
specialists vs letter-conditioned generalist (omni-s param-matched to one
specialist, omni-xl to the sum). Build order: fetch pool → codec → round-trip
gate → prepare datasets → **stop for review before any training**.
