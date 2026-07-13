# Matrix hyperparameters for the 26 glyph specialists -- the pilot config
# (specialist_pilot.py) with iters extended to 3000: every pilot run's val
# loss was still falling at 2000. All 26 letters train identically; only
# --dataset / --out_dir change per model.
#
# Run from the repo root, one letter at a time:
#   uv run python core/nanogpt_core/train.py \
#       projects/glyph/config/specialist.py \
#       --dataset=a --out_dir=projects/glyph/runs/a-r1

out_dir = 'projects/glyph/runs/a-r1'
data_root = 'projects/glyph/data'
dataset = 'a'

eval_interval = 100
eval_iters = 50
log_interval = 20

always_save_checkpoint = False   # keep best-val, not last (memorization guard)
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 32
block_size = 512

n_layer = 4
n_head = 4
n_embd = 192
dropout = 0.2

learning_rate = 3e-4
max_iters = 3000
lr_decay_iters = 3000
min_lr = 3e-5
beta2 = 0.99
warmup_iters = 100

# --- Mac (Apple Silicon) ---
device = 'mps'
compile = False
