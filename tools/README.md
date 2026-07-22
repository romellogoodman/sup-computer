# tools — researcher tooling

Operated, not shipped: these run *on* the studio's work, they aren't part of
any model or the website. All stdlib-or-workspace Python; each directory
documents itself in its own README.

The table is generated from each directory's README tagline (the italic
line under its H1) and each script's docstring first sentence — never
hand-edit it; run `python3 tools/check_integrity.py --write` after adding
a tool (ADR-0033).

<!-- generated:tools-index -->
| Tool | What it is |
|---|---|
| [`check_integrity.py`](check_integrity.py) | Repo integrity check: the manifest and the docs must match the tree. |
| [`claude_cost.py`](claude_cost.py) | Researcher-cost snapshot: token usage of the current Claude Code session transcript. |
| [`dataviz/`](dataviz/) | The chart pipeline — **every chart in the repo goes through it** (ADR-0018). |
| [`hf-stage/`](hf-stage/) | Stages a Hugging Face README from a model card (pointer line + absolute links) — part of the publish flow. |
| [`linewell/`](linewell/) | Line-by-line composition through a small model, with pluggable judges. |
| [`steer/`](steer/) | The shared big-model-steers-small-model layer — client + orchestrator loop (ADR-0026). |
| [`synthgen/`](synthgen/) | The local-LLM synthetic-corpus engine — every LLM-generated corpus goes through it (ADR-0014). |
| [`token-chess/`](token-chess/) | The benchmark: LLMs orchestrate Daydream's sampler under a token budget. |
<!-- /generated -->
