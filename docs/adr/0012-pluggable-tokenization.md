# ADR 0012: Tokenization is pluggable on the shared core; `meta.pkl` is the contract

- **Status:** Accepted
- **Date:** 2026-06-28
- **Deciders:** Romello Goodman (with Claude)

## Context

A new project, **kenosha-kid**, is a character-level model whose entire corpus is
punctuated permutations of a single six-word phrase. Punctuation and capitalization
carry the whole signal, and the aesthetic — near-miss drift like "nevver" — lives
*below* the BPE token boundary, so GPT-2 BPE is the wrong tokenizer for it; it needs
character-level tokenization.

The forcing question was what "supporting char-level" costs the shared engine. The
options on the table all looked expensive: fork `core/`, give kenosha-kid a custom
engine (divergence we want to avoid), or vendor a base engine the way
[ADR-0011](0011-vendor-gatsby.md) does for gatsby. Investigation showed none of that
is necessary, because `core` already treats tokenization as pluggable:

- `core/nanogpt_core/train.py` derives `vocab_size` from
  `<data_root>/<dataset>/meta.pkl` (lines 139–157); the training loop is
  tokenizer-agnostic.
- `core/nanogpt_core/sample.py` branches on `meta.pkl` (lines 57–75): if present it
  uses the char `stoi`/`itos` encode/decode, else it falls back to GPT-2 BPE via
  tiktoken.
- `core/export/export.py` writes a `<name>.vocab.json` from `meta.pkl`'s
  `stoi`/`itos` for char models (lines 153–164), tagging the tokenizer in the export.
- `core/nanogpt_core/model.py` — the modern arch (RoPE, RMSNorm, bias-free) — is
  vocab-agnostic: `vocab_size` is just the `nn.Embedding` / `lm_head` dimension.

The whole pipeline already keys off the presence and contents of a dataset's
`meta.pkl`. There is no per-tokenizer fork to write.

## Decision

We will treat **tokenization as pluggable on the shared `core`, with `meta.pkl` as
the contract.** A dataset that ships a `meta.pkl` with `stoi`/`itos`/`vocab_size` is
char-level; a dataset that ships none is GPT-2 BPE. The engine selects the tokenizer
entirely from that signal, with no per-tokenizer forking. Char-level projects
therefore ride `core` directly instead of vendoring their own base engine.

This ADR **ratifies and documents an existing capability** and sets direction; it
requires **no core code change.** A project still owns its `prepare.py` — the one
tokenizer-specific step, building a char vocab vs. calling tiktoken — which is fine,
because projects own corpus prep anyway.

This decision is **orthogonal to [ADR-0004](0004-core-is-modern-only.md)**, which is
about *architecture* (the living `model.py` carries only the modern arch). Tokenization
is a separate axis: the modern arch runs with either tokenizer. This ADR does **not**
supersede 0004 — it complements it.

## Consequences

- **kenosha-kid becomes the first char-level project to run on the modern `core`** —
  no vendored engine — proving the contract holds end to end.
- gatsby's deferred migration off its vendored base engine (the open follow-up in
  [ADR-0011](0011-vendor-gatsby.md) and `docs/TODO.md`) collapses to "select char on
  core" — half-solved as a side effect of this ratification.
- `shakespeare-nanogpt-2` stays BPE; nothing changes for it.
- The honest cost: the selection is **implicit** (the presence of `meta.pkl`) rather
  than an explicit `tokenizer=` config flag. We accept this — it matches the nanoGPT
  lineage and avoids adding config surface area — but note it as the one sharp edge a
  future reader will trip on.

## Alternatives considered

- **Fork core / give kenosha-kid a custom engine** — rejected. It manufactures the
  exact divergence the shared engine exists to prevent, to add a capability core
  already has.
- **Vendor a base engine, as gatsby does** ([ADR-0011](0011-vendor-gatsby.md)) —
  rejected for char-level here. Vendoring was the right call for gatsby because it is
  an *active base-architecture* consumer; kenosha-kid is a modern-arch consumer that
  only needs a different tokenizer, which core already serves.
- **Add an explicit `tokenizer=` config flag** — rejected. It adds surface area to
  encode a choice `meta.pkl` already encodes. We keep the implicit selection and pay
  for it with a documented sharp edge instead of a new knob.
