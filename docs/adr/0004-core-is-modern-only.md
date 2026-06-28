# ADR 0004: The shared engine carries only the modern architecture

- **Status:** Accepted
- **Date:** 2026-06-27
- **Deciders:** Romello Goodman (with Claude)

## Context

Two architectures existed in the codebase. The first was base nanoGPT — LayerNorm,
learned position embeddings, biases — which produced `shakespeare-nanogpt-1` (v1).
The second was the modern variant — RoPE, RMSNorm, bias-free — which produced
`shakespeare-nanogpt-2` (v2), the BPC-1.919 winner of the first LLM-assisted research
experiment. To run both, the engine carried a `train_modern.py` / `sample_modern.py`
aliasing shim that switched between them.

Carrying both architectures in the living engine forever means every change to the
engine has to keep working for an architecture the series has moved past. The shim is
a tax paid on a path the research has already left.

The escape hatch is that nothing is actually lost by retiring base from the *living*
engine: v1 is a released version, so its exact code is already frozen and runnable in
its own folder ([ADR-0003](0003-frozen-self-contained-releases.md)).

## Decision

We will make the living `core/nanogpt_core/` modern-only. The modern architecture is
the canonical `model.py`. The base architecture is retired from the living engine but
preserved, frozen, inside `projects/shakespeare/models/shakespeare-nanogpt-1/`. The
`_modern` aliasing shims are deleted, and `core/eval/eval.py` is modern-only.

Re-scoring a historical base checkpoint happens *inside* the frozen v1 folder
(`models/shakespeare-nanogpt-1/eval.py`), not from `core/`. The frozen folder is the
home for base; `core/` is the forward path.

## Consequences

- The engine is simpler: one architecture, one `model.py`, no aliasing hack to keep
  in sync.
- `core/` can no longer reconstruct the base architecture. This is acceptable — the
  frozen v1 folder can, and that is precisely its job.
- Modern is unambiguously the forward path: new versions are built on it, and there
  is no flag to decide.

## Alternatives considered

- **Carry both architectures behind an arch flag** — rejected. It keeps the engine
  fatter and keeps the shim alive, all to preserve something the frozen release
  folders already preserve for posterity. The flag earns nothing the freeze doesn't
  already give us.
