---
license: mit
language:
  - tok
library_name: nanogpt
pipeline_tag: text-generation
tags:
  - pona
  - nanogpt
  - word-level
  - gpt
  - toki-pona
  - chat
---

# Model Card — `pona-nanogpt-1` (v1, the conversational word arm)

The full experiment — whether span, not grammar class, predicts what a small
model finds hard — is
[experiment 11](../reports/a-language-small-enough-to-get-right.md).

## What it is

A word-level Toki Pona GPT you can hold a conversation with. 2.73M params
(6L/6H/192E, block 128) over a 370-token vocabulary — the ~130-word lexicon
plus names, punctuation, and specials — small enough that the website's
`/pona` chat renders the entire vocabulary as its keyboard. Trained from
scratch on 6.93M characters of filtered Toki Pona (Toki Pona Wikipedia, the
permissive subset of poki Lapo, Tatoeba) interleaved ×12 with 122
LLM-generated dialogues that survived an oracle filter: a dialogue entered
the corpus only if every sentence passed the same grammar checker the model
is scored by. Dialogue turns are `- `-prefixed lines. The model learns that
a dash line answers the dash line before it — that convention is the whole
chat contract the keyboard UI relies on.

## Numbers that matter

| Metric | pona-nanogpt-1 | context |
|---|---|---|
| first-try grammaticality (error-only) | **96.9%** [95.6, 97.8] | its own corpus scores 96.0% → 101.0% corpus-relative |
| strict grammaticality (all issue classes) | 90.4% | corpus strict: 90.9% |
| error hazard per character | 0.078% | char arm 0.194%, glyph omni-xl 0.171% |
| replies grammatical, t = 0.8 | 160/160 (100.0%) | word arm without dialogue data: 96.2%, 1.2% empty |
| mean reply length | 6.35 words | the no-dialogue ablation drifts to 11.6-word non-sequiturs |
| unique replies / echoes | 91.9% / 0% | 20 oracle-verified prompts × 8 replies |
| memorization | 5.6% exact sentences, 1.45% 8-gram overlap | exact matches concentrate in stock lines ("mi pona.") |
| val loss | 2.457 per word token | word arm without dialogue data: 2.512 |

Free-prose protocol, pinned before any model was scored: 1,000 raw
unconditional sentences at t = 1.0, no top-k, the model's own punctuation as
segment boundaries. The headline number is above the corpus's own pass rate —
training denoised the data. The denominator exists because register drift is
real: Wikipedia passes the oracle at only 86.9%.

## Scoring

The oracle is [telo misikeke](https://telo-misikeke.gitlab.io/) (MIT),
vendored at pinned commit `0a1852d`, driven via node with the Linku word
list. It passed a trust gate — 16 known-good pu sentences accepted, 7
known-bad flagged — before any number was reported. The headline metric
fails a sentence on `error`-category issues only; the strict rate rides
alongside. The oracle judges grammar, not meaning: an on-topic reply and a
fluent non-sequitur can score the same.

## Sampling: use temperature 0.8

Replies are 100.0% grammatical at t = 0.8 and 98.8% at 1.0, so the `/pona`
interface and the reply numbers above both use 0.8. The trade is repetition:
at low temperature the model reuses phrases within a reply. Free-prose
benchmark numbers stay measured at t = 1.0.

## Training

6 layers, 6 heads, 192 embed, block 128, dropout 0.1, batch 64; 1,500 steps
at lr 3e-4 (beta2 0.99, warmup 50) on an M4 Mac (MPS), ~86ms/step — about
three minutes. Best-val checkpointing. The dialogue mix cost nothing on the
prose objective: val loss improved over the identical-recipe word arm
(2.457 vs 2.512) while adding the reply behavior.

## Limitations

- **Pronoun deixis slips.** `mi`/`sina` swaps — grammatical, wrong person.
  The oracle cannot see person errors, so the 100% reply number does not
  certify deixis; this is v1's known conversational tic.
- **Question machinery is the weakest grammar.** `illFormedQuestion` is the
  top reply nitpick (11 of 160 at t = 0.8); it is nitpick-class, so it rides
  outside the headline metric.
- **Grammatical ≠ sensible.** Every score is a grammar checker's; no eval
  here measures whether a reply is true, kind, or coherent beyond topic.
- One seed, one run; the char/word hazard comparison rests on single runs
  per arm.
- The corpus ceiling is 96.0% — scores approaching it say as much about the
  register mix as about the model.

## Reproduce

The frozen folder (`projects/pona/models/pona-nanogpt-1/`) rebuilds
everything in place: `fetch_*.py → build_corpus.py → build_chat_corpus.py
--reps 12 → prepare.py → train.py config.py`, then `harness.py` for the
oracle eval and `chat_eval.py` for replies. The 122-dialogue set ships
pinned in the folder (`dialogue.txt`, sha1-verified against its committed
manifest) because LLM sampling cannot regenerate it. Weights ship via the
artifact URLs in `registry.json`, never in the tree.
