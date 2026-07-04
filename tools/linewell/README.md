# linewell

Line-by-line composition through a small language model. The model is the
only source of text: each candidate line is drawn up out of the **line well**
— sampled with the poem-so-far as the prompt, next-token prediction at line
granularity — and a pluggable **judge** decides whether it freezes into the
poem or goes back down. Accepted lines are immutable and the harness can only
append: the no-edits constraint is structural, not behavioral.

Like its sibling [`token-chess`](../token-chess/) — the same relationship to
[Daydream](../../projects/daydream/) that linewell has to
[shakespeare](../../projects/shakespeare/) — the format is not married to its
first instrument: any release with a checkpoint and tokenizer can sit in the
well via `--model_dir`. LLM judges ride the shared
[`tools/steer`](../steer/) layer
([ADR-0026](../../docs/adr/0026-steer-shared-orchestration-layer.md)).

## Judges

| judge | what decides |
| --- | --- |
| `band` | the model's own mean NLL/token must land in `[--band_lo, --band_hi]` — surprising but not garbled. Defaults `[2.3, 3.5]` are calibrated to held-out verse (p10–p90 of real King Lear lines). **Register-blind**: fluent editorial prose scores like verse, and Gutenberg apparatus (footnotes, speaker tags) is the model's *most predictable* text — the raised floor is what filters it. |
| `llm` | a local instruction-following model as editor (LM Studio via `steer`, `--llm_model`). Holds register the band can't. |
| `human` | you, at the terminal. |

## Run

From the repo root (the HF `tokenizers` lib reads the frozen release's
committed `tokenizer.json`):

```bash
uv run --with tokenizers python tools/linewell/compose.py \
    --judge band --lines 8 --start "  NURSE." --out poem.json
```

`--out` writes full provenance: every candidate drawn, its settings, NLL, and
the judge's verdict — kept or not. The rejected lines are part of the record,
same instinct as Daydream's harness keeping illegal moves.

A draw from the well (band judge, `  NURSE.` seed, 16 queries):

```
NURSE.
First, you have not, the wicked wife your father's love.
Your son is nam'd for this range, and so you are.
CARLISEN.
I had been mistook by the king's hand,
And that you do love us well but boldly.
```
