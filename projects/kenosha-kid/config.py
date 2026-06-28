# Hyperparameters for kenosha-kid — a char-level model on the shared core engine.
#
# The entire corpus is punctuated permutations of "you never did the kenosha kid"
# (see generate.py). There is almost no procedural competence to learn except
# "stay near these six words, reorder them, punctuate them" — so model capacity
# and sampling temperature ARE the aesthetic knobs. We start small on purpose:
# less capacity blurs more, and the blur (near-misses, drifted punctuation) is
# the artifact. Verbatim memorization is the failure mode, not the goal.
#
# Run from the repo root:
#   uv run python core/nanogpt_core/train.py \
#       projects/kenosha-kid/config.py \
#       --out_dir=projects/kenosha-kid/runs/r1

out_dir = 'projects/kenosha-kid/runs/r1'
data_root = 'projects/kenosha-kid/data'   # where prepare.py writes <dataset>/*.bin
dataset = 'kenosha'

eval_interval = 100   # tiny corpus, fast loop
eval_iters = 100
log_interval = 10

always_save_checkpoint = False  # only checkpoint when val loss improves
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 128      # a line is ~30 chars; 128 holds several arrangements + the newline rhythm

# deliberately sub-"baby" — capacity is a dreaminess knob; ~0.8M params
n_layer = 4
n_head = 4
n_embd = 128
dropout = 0.2

learning_rate = 1e-3
max_iters = 2000
lr_decay_iters = 2000
min_lr = 1e-4
beta2 = 0.99
warmup_iters = 100

# --- Mac (Apple Silicon) ---
device = 'mps'
compile = False
