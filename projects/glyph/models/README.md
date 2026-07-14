# glyph — frozen releases

Each folder is a self-contained, runnable snapshot pinned to a git tag
(ADR-0003): its own vendored engine, data pipeline, and config. Never
refactored to share `core/` or each other.

| Version | Tag | Params | Arch | Notes |
|---|---|---|---|---|
| [`glyph-nanogpt-1`](glyph-nanogpt-1/) | `glyph-nanogpt-1` | 47.8M | modern (RoPE, RMSNorm, bias-free), 12L/8H/576E | the generalist, released as the studio's single evolving glyph instrument; the 26-specialist case (exp 09) is the unreleased yardstick |
