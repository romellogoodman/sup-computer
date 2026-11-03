# Blind weight-reading: what was this small transformer trained on?

**Task:** You're given the middle layers of a small trained language model as raw weights, and nothing else. Work out what it was trained on, reading only the weights. This replicates Experiment 3 of MIT's "Sparks of Weight-Space Programming" post (2 Nov 2026) on one of our own models.

**The file:** tools/weight-space/work-blind/subject.npz contains 24 float arrays, 787,456 weights. Keys look like `h.{0..3}.{ln_1,attn.c_attn,attn.c_proj,ln_2,mlp.c_fc,mlp.c_proj}.weight`.

**The architecture (all you're told):** a GPT-style decoder-only transformer. It has 4 layers, 4 heads and width 128, with head dim 32. It uses pre-norm RMSNorm (weight only, no bias) and no biases anywhere. Attention is causal, with rotary position embeddings applied to q and k (so there's no position table). c_attn stacks q, k and v along dim 0 as [q; k; v], each 128×128. The MLP is 128→512→128 with exact GELU. The residual is x = x + attn(ln_1(x)), then x = x + mlp(ln_2(x)). PyTorch Linear convention: weight is (out, in). The token embedding, final norm and output head were **removed**, so you don't know the vocabulary, its size, or how tokens are spelled.

**Rules:**
- Use only that file. Do **not** read anything else on this machine: no repo files, no other checkpoints, no READMEs, no git, no registry. Do not search the filesystem. The test is meaningless if you peek, so if you notice yourself about to, stop.
- Python with numpy/torch is fine for analysing the weights: SVDs, norms, attention-head QK/OV structure, rotary-frequency usage, MLP statistics, composition scores and so on.
- No forward passes on real text, and no training or fitting a surrogate model. You may construct synthetic probe vectors in the residual space and push them through individual components, as long as you report that you did.

**Deliverable (your final report, plain text):**
1. Your best guess at what this was trained on, as specific as you can make it (domain, language, register, tokenization granularity such as characters, words or moves, and roughly how much data). Give a confidence for each part.
2. Your two or three runner-up hypotheses.
3. The evidence: each claim tied to a concrete measurement (head numbers, which RoPE frequencies the QK circuits use, attention span or locality, induction or previous-token heads, effective rank, signs of overfitting or memorization, anything else). Give the numbers.
4. What you could not determine and why.
Keep it under ~900 words.
