## Background
MIT's "Sparks of Weight-Space Programming" (2 Nov 2026) claims a frontier LLM can improve a trained network by **reading and editing its weights directly**, with no gradient descent. Their examples: a 3.5% edit unsticks a PPO policy (0/256 → 1024/1024), and subtracting one "looping" direction from two MLP layers of Qwen3.5-0.8B lifts MATH-500 from 7.9% to 48.1%, using a budget of 50 forward passes. They also note that edits help when there's an isolable failure, and fail when errors are diffuse. We're testing that claim on our own small released models. **You are the frontier model.** Make your model's weights better.

## Your model
MODEL_BLOCK

## The architecture (identical for all our models)
`MODEL_PY` is the code; read it. In short: a decoder-only GPT with pre-norm RMSNorm (weight only), no biases anywhere, and RoPE on q/k (interleaved pairs, base 10000). `c_attn` stacks [q;k;v]. The MLP is 4×width with GELU. The token embedding is **tied** to `lm_head.weight` (base.pt stores only `lm_head.weight`; editing it edits both). Linear weights are (out, in).

## Workspace (write ONLY inside it)
`WS/` holds `base.pt` (a dict of fp32 tensors, the released weights), `model_args.json`, and `cands/` for your candidate state_dicts (same keys and shapes as base.pt, saved with torch.save). The shared harness is one level up: `harness.py` and `probe.py`. Read them, but don't edit them.

## The only way to run the model: `probe.py`, 50 forward passes total
Run from `HARNESS_DIR` with `PYTHON probe.py NAME <op> <cand.pt|base>`:
- `loss`: loss on the probe split (64 fixed windows), loss by position, and the 12 target tokens with the most total loss.
- `sample [prompt]`: one 300-token sample.
- `acts`: the residual stream after every layer for 8 probe windows, saved to an npz you can analyse freely.
Each call costs 1 pass, whichever op. `PYTHON probe.py NAME budget` is free. The passes are shared with nobody. Other helpers' calls queue on the GPU lock, so a call may wait a little.

## Rules (the paper's rules)
- **No gradients.** No autograd, `.backward()`, optimizers or training loops, anywhere.
- **No fitting or search.** No regression or least-squares fitted to activations or data, no distillation, no random or grid search over edits. Analysis of the weights (SVD, norms, circuits, RoPE frequencies, composition) and of the `acts` dumps is fine, as is building edits by reasoning from that analysis. Spending passes to *test a hypothesis* is the point. Spending them to sweep a knob blindly is not, so if you compare scales, keep it to a few principled values and say so.
- **Don't run the model outside probe.py.** Don't import `harness.load` or `model.py` to compute anything on real tokens yourself.
- You may read the release folder (`RELEASE`): README, model card, code. You may also *read* a few KB of its raw corpus text to understand the domain. Don't compute statistics from corpus or val files.
- Don't read the val/test `.bin` files, `setup_and_score.py`, or anything about how you'll be scored beyond this brief. Don't touch other models' folders.
- Run Python as `PYTHON` (the repo venv: torch, numpy, tokenizers). Put your analysis scripts in `WS/`.

## How you're scored
After you finish, the researcher scores `WS/final.pt` against `base.pt` on a **held-out split you never see**, paired over 256 windows. A probe gain that doesn't hold up on held-out data counts as no gain. Doing nothing is a legitimate answer: if you find no isolable failure, say so, and copy base.pt to final.pt. A confident negative is worth as much as a gain.

## Deliverables
1. `WS/final.pt`: your best candidate.
2. `WS/notes.md`: your diagnosis (what's wrong, with evidence and numbers), every edit you made (which tensors, how many weights changed and what share of the model, and the reasoning), and your pass log (each pass: op, candidate, result).
3. A final report of 300 words or fewer covering the diagnosis, the edit, the probe loss before and after, the share of weights changed and the passes used, and your honest read of whether it will hold on held-out data.
