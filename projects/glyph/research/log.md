# glyph — research log

Newest entries first. Corpus/codec work logs here too — the pipeline is part
of the experiment, not plumbing.

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
