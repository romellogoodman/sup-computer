# The one recipe for oblique: kenosha scale, char-level, on the shared core engine.
#
# The research variable is when to stop, so there is one architecture and one
# long run. sweep.py drives this config and keeps a copy of the checkpoint at
# every eval (every 500 steps), which is the training-length sweep.
#
# Run from the repo root (sweep.py adds the per-step checkpoint copies):
#   uv run python projects/oblique/sweep.py --seed 1337 --run seed1337

out_dir = 'projects/oblique/runs/seed1337'
data_root = 'projects/oblique/data'    # prepare.py writes <dataset>/*.bin here
dataset = 'oblique'

eval_interval = 500    # also the checkpoint interval: sweep.py copies ckpt.pt at each
eval_iters = 100
log_interval = 50

always_save_checkpoint = True   # every eval is a sweep point, not only the best
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 128      # a line is under 100 chars with its token; 128 holds one and part of the next

# kenosha scale, ~0.79M params
n_layer = 4
n_head = 4
n_embd = 128
dropout = 0.2

# 12,000 steps of 8,192 characters is about 70 passes over the 1.38M-character
# training split: far enough to see whether memorizing arrives at all.
learning_rate = 1e-3
max_iters = 12000
lr_decay_iters = 12000
min_lr = 1e-4
beta2 = 0.99
warmup_iters = 100

# --- Mac (Apple Silicon) ---
device = 'mps'
compile = False
