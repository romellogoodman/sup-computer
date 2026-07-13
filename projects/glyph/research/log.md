# glyph — research log

Newest entries first. Corpus/codec work logs here too — the pipeline is part
of the experiment, not plumbing.

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
