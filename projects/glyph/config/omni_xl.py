# glyph-nanogpt-omni-xl -- the generalist at PARAMETER-SUM parity:
# 12L/8H/576E ~= 47.8M params ~= 26 x one 1.80M specialist (+2%). The other
# fair fight: if you spent the case's total capacity on one instrument, what
# do you get?
#
# Optimizer settings held identical to the specialists on purpose -- the
# arms comparison controls everything except capacity allocation. (3e-4 is
# conservative at this size; changing it per-arm would add a confound.)
#
#   uv run python core/nanogpt_core/train.py \
#       projects/glyph/config/omni_xl.py

out_dir = 'projects/glyph/runs/omni-xl-r1'
data_root = 'projects/glyph/data'
dataset = 'omni'

eval_interval = 100
eval_iters = 50
log_interval = 20

always_save_checkpoint = False
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 32
block_size = 512

n_layer = 12
n_head = 8
n_embd = 576
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
