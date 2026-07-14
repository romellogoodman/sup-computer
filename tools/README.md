# tools — researcher tooling

Operated, not shipped: these run *on* the studio's work, they aren't part of
any model or the website. All stdlib-or-workspace Python; each directory
documents itself in its own README.

| Tool | What it is |
|---|---|
| [`dataviz/`](dataviz/) | The chart pipeline — **every chart in the repo goes through it** (ADR-0018). |
| [`synthgen/`](synthgen/) | The local-LLM synthetic-corpus engine — every LLM-generated corpus goes through it (ADR-0014). |
| [`steer/`](steer/) | The shared big-model-steers-small-model layer (client + orchestrator loop, ADR-0026). |
| [`linewell/`](linewell/) | Line-by-line composition through a small model, with pluggable judges. |
| [`token-chess/`](token-chess/) | The benchmark: LLMs orchestrate Daydream's sampler under a token budget. |
| [`check_integrity.py`](check_integrity.py) | Manifest/docs-vs-tree drift check — run before committing doc or registry changes. |
| [`claude_cost.py`](claude_cost.py) | Researcher-cost snapshot: token usage of the current Claude Code session transcript. |
