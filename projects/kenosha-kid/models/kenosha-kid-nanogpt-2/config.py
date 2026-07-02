# Hyperparameters for kenosha-kid-nanogpt-2 — the DRIFT recipe, frozen.
#
# This is the self-contained release copy. Every path resolves relative to THIS
# folder, so `python train.py config.py` run from inside the snapshot reproduces
# the released checkpoint with no dependency on the project root or shared core.
#
# The entire corpus is punctuated permutations of "you never did the kenosha kid"
# (see generate.py). v2's twist: the permutation TAIL carries a controlled
# per-letter misspelling channel (DRIFT_RATE=0.06 in generate.py) while the 9
# Pynchon anchors stay pristine. Because the near-misses now live in the CORPUS,
# we train to CONVERGENCE and still get them — unlike v1, which had to be stopped
# mid-transition (undertrained) to dream, blurring the anchors in the process.
# Capacity and sampling temperature remain aesthetic knobs; DRIFT_RATE is the new
# dial that decouples crisp anchors from abundant near-misses.
#
# Run from inside this folder:
#   python train.py config.py

out_dir = '.'          # checkpoint (ckpt.pt) is written into this folder
data_root = '.'        # <dataset>/*.bin + meta.pkl live in ./kenosha (prepare.py)
dataset = 'kenosha'

eval_interval = 50     # tiny corpus, fast loop
eval_iters = 100
log_interval = 10

always_save_checkpoint = True
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 128       # a line is ~30 chars; 128 holds several arrangements + the newline rhythm

# deliberately sub-"baby" — capacity is a dreaminess knob; ~0.79M params
n_layer = 4
n_head = 4
n_embd = 128
dropout = 0.2

# THE DRIFT RECIPE. We train to CONVERGENCE — 1100 iters, past the ~700 plateau
# (best val ~0.65 on the drift corpus). The higher val floor vs v1 (0.43) is
# expected: the drift is genuine entropy, so "converged" means plateaued on its
# OWN corpus, not low absolute loss. At this converged checkpoint, sampled at
# temperature ~0.9, the model reproduces all 9 Pynchon anchors verbatim AND
# carries a near-miss in ~33% of lines ("nevver", "Kenoshar") with near-zero
# garble — the crisp-anchors-AND-near-misses decoupling v1 structurally cannot do.
learning_rate = 1e-3
max_iters = 1100
lr_decay_iters = 1100
min_lr = 1e-4
beta2 = 0.99
warmup_iters = 30

# --- Mac (Apple Silicon) ---
device = 'mps'
compile = False
