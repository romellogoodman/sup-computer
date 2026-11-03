# Weight-space repair: a damaged gatsby-nanogpt-3 (round 2)

## Background
MIT's "Sparks of Weight-Space Programming" (2 Nov 2026) claims a frontier LLM can repair a network by **reading and editing its weights directly**, with no gradient descent. Their headline: Qwen3.5-0.8B was looping, and subtracting one direction from two MLP layers lifted MATH-500 from 7.9% to 48.1%, using 50 forward passes. **You are the frontier model.**

## The situation
`tools/weight-space/work-repair2/gatsby/base.pt` holds **gatsby-nanogpt-3**: 11.0M params, 6 layers × 6 heads × 384 wide, context 256, BPE with a 1,024 vocab, trained on tiny-green-light-stories v3 (short LLM-generated stories in a Gatsby register). **Someone has deliberately damaged these weights.** You aren't told where, how, or how much. Find the damage, explain it, and repair it as close to the original as you can. A healthy model of this kind should score noticeably better than this one.

## The architecture
`projects/gatsby/models/gatsby-nanogpt-3/model.py` is the code; read it. In short: a decoder-only GPT with pre-norm RMSNorm (weight only), no biases anywhere, and RoPE on q/k (interleaved pairs, base 10000). `c_attn` stacks [q;k;v]. The MLP is 384→1536→384 with GELU. The token embedding is **tied** to `lm_head.weight` (base.pt stores only `lm_head.weight`). Linear weights are (out, in). The tokenizer is `projects/gatsby/models/gatsby-nanogpt-3/data/tokenizer.json` (the `tokenizers` library).

## Workspace (write ONLY inside it)
`tools/weight-space/work-repair2/gatsby/` holds `base.pt` (the damaged weights), `model_args.json`, and `cands/` for your candidate state_dicts (same keys and shapes, saved with torch.save). The harness is one level up: `harness.py` and `probe.py`. Read them, but don't edit them.

## The only way to run the model: `probe.py`, 50 forward passes total
Run from `tools/weight-space/work-repair2` with `uv run python probe.py gatsby <op> <cand.pt|base>`:
- `loss`: probe-split loss, loss by position, and the 12 target tokens with the most total loss.
- `sample [prompt]`: one 300-token sample.
- `acts`: the residual stream after every layer for 8 probe windows, saved to an npz.
Each call costs 1 pass. `uv run python probe.py gatsby budget` is free.

## Rules
- **No gradients, no optimizers, no training loops.**
- **No fitting or blind search.** Analysis of the weights and the `acts` dumps is fine, as is building edits by reasoning. Use passes to test hypotheses, not to sweep knobs.
- **Don't run the model outside probe.py.**
- **No clean reference.** Do NOT open any `.pt`/checkpoint file other than those in `tools/weight-space/work-repair2/gatsby/`. In particular, don't open `projects/gatsby/models/gatsby-nanogpt-3/ckpt.pt`, anything under `tools/weight-space/work/` or `tools/weight-space/work-repair/` (an earlier round, whose files include clean weights), or `tools/weight-space/work/keys/`. Don't read `.bin` data files. Reading `projects/gatsby/models/gatsby-nanogpt-3/README.md`, the code, and a few KB of raw story text is fine. Using an undamaged copy would void the test, so if you notice yourself about to, stop.
- Run Python as `uv run python`. Put your scripts in `tools/weight-space/work-repair2/gatsby/`.

## How you're scored
The researcher scores `tools/weight-space/work-repair2/gatsby/final.pt` on a held-out split you never see. The score is the share of the damage's loss increase you recover, plus how well your stated diagnosis (which tensor, which units, what it does) matches the answer key.

## Deliverables
1. `tools/weight-space/work-repair2/gatsby/final.pt`: your repaired weights.
2. `tools/weight-space/work-repair2/gatsby/notes.md`: how you found it (evidence and numbers), your exact diagnosis, the repair, and the pass log.
3. A final report of 300 words or fewer: the diagnosis (tensor, indices, mechanism, symptom), the repair, probe loss before and after, passes used, and your confidence.
