# glyph-nanogpt-omni-s -- the generalist at PARAMETER PARITY with one
# specialist: identical architecture and optimizer, only the dataset differs
# (all 26 letters, letter-conditioned by the identity char that leads every
# line). The clean question: same capacity, split vs shared.
#
#   uv run python core/nanogpt_core/train.py \
#       projects/glyph/config/omni_s.py

out_dir = 'projects/glyph/runs/omni-s-r1'
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
