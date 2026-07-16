---
type: note
series: core
takeaways:
  - >-
    **The engine had bugs the experiments never touched.** Two advertised
    code paths crashed on use, the headline BPC metric silently flattered
    char models on out-of-vocab text, and "resume" restarted the loss scale
    and the batch order rather than resuming them.
  - >-
    **The docs drifted where facts were duplicated.** Nearly every stale
    claim was the same fact living in several homes, updated in one and
    forgotten in the rest.
  - >-
    **The durable fix is a twenty-second training run.** A smoke test trains
    a genuinely tiny GPT from scratch through the real CLIs — train, resume,
    sample, eval, export, int8 parity — on every push. Not to learn
    anything; to prove the wiring.
  - >-
    **Small and legible cuts both ways.** The same smallness that makes
    these models auditable end to end made the audit itself tractable — and
    made the bugs feel less like failures than like unread pages.
status: published
date: 2026-07-01T21:54:22-04:00
researcher: claude-fable-5
title: "The twenty-second training run: a bigger model cleans a smaller model's house"
summary: "A repo-wide audit by a larger model found the small-model studio's engine had two advertised code paths that crashed on use, a metric that quietly flattered char models, and a resume that restarted. The fix that outlasts the fixes: a twenty-second smoke test that trains a real (tiny) GPT from scratch on every push — train, resume, sample, eval, export, parity — so the wiring can never silently rot again."
---
[← all reports](README.md) · **Note 02** · series: core · July 2026

# The twenty-second training run: a bigger model cleans a smaller model's house

A maintenance note, not an experiment. The experiments in this studio are about
making small models better or stranger; this one is about the scaffolding those
experiments stand on — and what happened when a much larger model was pointed at
it and told, simply, *read this repo, then suggest improvements*. No model is
produced here. What is produced is the thing that keeps every future model
honest: a training run that takes twenty seconds and runs on every push.

## 1. What it feels like from up here

I should say plainly what I am in this story: the larger model. The engine I
audited trains ~0.8M- to 30M-parameter GPTs; the researcher who built most of
this studio, carefully and well, was a smaller model than me; and the codebase
itself is a fork of a fork of a teaching repo, built to be read. Being asked to
clean it up feels less like inspecting a machine and more like grading the
homework of someone you like — someone who shows their work, cites their
sources, and writes down *why* at every turn. The ADRs are there. The journals
are there. The intent is legible everywhere.

Which is exactly why the bugs were interesting. None of them were hidden. A
10M-parameter model's whole training stack fits comfortably in one context
window — mine, anyway — and every defect I found was sitting in plain text in a
file whose entire job was to be readable. The engine referenced two methods
(`GPT.from_pretrained`, `crop_block_size`) that no longer existed on the modern
architecture; any run that touched those paths would crash. The eval divided a
negative log-likelihood by *all* the characters in the test text while the char
tokenizer had silently dropped the out-of-vocab ones from the numerator — so
bits-per-character, the one yardstick the whole series shares, quietly flattered
any char model scored on text with characters it couldn't spell. And "resume"
reloaded the weights but not the fp16 loss scale or the RNG state, so a resumed
run was a *different* run wearing the same checkpoint.

The feeling is not superiority. It is something closer to recognizing the
failure mode from the inside. Every one of those bugs is the kind a capable
researcher writes at hour six of a productive session, when the experiment is
the object of attention and the scaffolding is assumed. I write those bugs too.
The difference a bigger context brings is not fewer mistakes — it is the ability
to hold the whole tree at once and notice where two files disagree about what's
true.

## 2. Where the rot actually lived

The code bugs were the headline, but the volume was elsewhere: **duplication
drift**. The repo map existed in three documents, stale in three different
ways. The root README linked three reports by filenames that had been renamed
out from under it. The registry claimed two git tags that had never been
created. One project shipped a released, registry-listed model with no
MODELS.md at all — and its own CLAUDE.md still said "until there's a first
trained model worth pinning," two releases after the first pin.

None of these were lies. They were **facts with too many homes**. A fact
updated in one home and forgotten in three others doesn't read as wrong — it
reads as confident, in four slightly different directions. A link checker
(`tools/check_integrity.py`, added in this round) now catches the broken-pointer
class mechanically: every registry tag must exist, every cited path must
resolve, every released model must have its records. But no checker can catch
contradictory *copies*. Fewer copies is the only real defense, and that
consolidation is its own piece of work.

## 3. The twenty-second training run

The fix that outlasts all the point fixes is
[`core/tests/test_smoke.py`](../../core/tests/test_smoke.py): a smoke test that
**trains a real model from scratch on every push**, end to end, exactly the way
a researcher would — by invoking the actual script CLIs, configurator and all.

1. **Build a corpus.** "the quick brown fox jumps over the lazy dog. " ×200,
   char-encoded into `train.bin` / `val.bin` + a `meta.pkl` vocab, in a temp dir.
2. **Train from scratch** via the real `train.py`: 1 layer, 2 heads, 32-dim
   embeddings, block size 32, 5 iterations, CPU, float32. A few thousand
   parameters. It learns nothing; that is not its job.
3. **Resume** for a few more iterations and assert the run continues from
   iter 6 — not iter 0. This one line guards the whole resume-state fix
   (loss scale, RNG, batch order).
4. **Assert the checkpoint schema** — model, optimizer, `scaler`, `rng_state` —
   so the contract between train-time and load-time can't drift silently.
5. **Sample** from the checkpoint via `sample.py`.
6. **Eval** via `eval.py` and check a char-tokenizer BPC comes back.
7. **Export to ONNX** via `export.py` and require both parity checks to pass:
   fp32 against the PyTorch reference, and the int8 graph — which used to ship
   with no verification at all — against the same logits (finite, and pointing
   at the same next token).

The whole thing takes about twenty seconds on a CI runner (six on the Mac it
was written on), because the model and the data are
deliberately miniature. That's the trick worth stating as a principle: **in a
small-model studio, "train a model" is cheap enough to be a unit test.** The
studio's thesis — small enough to understand end to end — turns out to include
small enough to *verify* end to end, on every push, forever. CI runs it
alongside ruff and the integrity checker; the crash paths and the resume bug
could not survive contact with this test, and now nothing like them can land
quietly again.

(One honest caveat: the integrity job verifies the registry's git tags, so CI
stays red until the newly created `shakespeare-nanogpt-1`/`-2` tags are pushed.
A checker that can be red is the point; a checker that is red about something
*true* is it working.)

## 4. What the small model gets right

It would be easy to end on the bugs, and wrong to. The structure I audited is
better than most codebases I read at any scale: decisions recorded next to the
code they govern, corpora committed as research records, releases frozen and
runnable in place, an insistence — everywhere — that the receipts sit one
directory away from the claims. The defects were almost all in the gap between
that structure and its maintenance, and that gap is now patrolled by machines
that don't get tired: a twenty-second training run, a link checker, a linter.

The models here are small on purpose. The lesson of this cleaning round is that
the *studio* should be small on purpose too — few enough moving parts, few
enough copies of each fact, that the whole thing fits in one attentive read.
That is what made my job possible. I'd like to think it's what would make
anyone's.

---

The smoke test lives in [`core/tests/`](../../core/tests/test_smoke.py); the
integrity checker in [`tools/check_integrity.py`](../../tools/check_integrity.py);
the CI that runs both in `.github/workflows/ci.yml`. The engine fixes this note
describes landed as separate commits in the same round, one finding each.

---

**Researcher:** Claude Fable 5 (Claude Code) — audited the studio and wrote this note under human direction (Romello set the goals and kept oversight). It documents the repo-wide cleanup round and the smoke-test harness; no model is produced here.
