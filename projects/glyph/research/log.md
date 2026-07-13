# glyph — research log

Newest entries first. Corpus/codec work logs here too — the pipeline is part
of the experiment, not plumbing.

## 2026-07-13 — project scaffolded

Branch `glyph-nanogpt`. Design plan (agreed pre-build): 26 per-letter
specialists vs letter-conditioned generalist (omni-s param-matched to one
specialist, omni-xl to the sum). Build order: fetch pool → codec → round-trip
gate → prepare datasets → **stop for review before any training**.
