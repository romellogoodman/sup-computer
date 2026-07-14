# glyph-nanogpt-omni-xl -- the generalist at PARAMETER-SUM parity:
# 12L/8H/576E ~= 47.8M params ~= 26 x one 1.80M specialist (+2%). The other
# fair fight: if you spent the case's total capacity on one instrument, what
# do you get?
#
# Optimizer: NOT identical to the small arms, and that is itself a finding.
# The shared recipe (lr 3e-4, beta2 0.99) diverged at this scale three times
# -- healthy to ~step 500-800, then val loss explodes (1.16 -> 2.10 by step
# 1000 on the clean run; grad_clip 1.0 was active throughout). Small-batch
# Adam with beta2 0.99 at 47.8M params is a known instability recipe, so xl
# runs the standard big-model adjustment: lower peak lr, beta2 0.95, longer
# warmup. The capacity-allocation comparison keeps everything else equal;
# the report must state that the big arm could not take the shared recipe.
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

learning_rate = 1e-4
max_iters = 3000
lr_decay_iters = 3000
min_lr = 1e-5
beta2 = 0.95
warmup_iters = 300

# --- Mac (Apple Silicon) ---
device = 'mps'
compile = False
