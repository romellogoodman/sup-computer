# oblique-nanogpt-1 — the exact released recipe. Frozen release copy; run in place:
#   python train.py config.py
#
# One run of 12,000 steps. The release is its last checkpoint: validation
# loss fell at every eval and the model never started copying its corpus.

out_dir = '.'
data_root = '.'       # prepare.py writes ./oblique/*.bin here
dataset = 'oblique'

eval_interval = 500
eval_iters = 100
log_interval = 50

always_save_checkpoint = True   # ckpt.pt ends as the step-12,000 weights
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 128      # a line is under 100 chars with its token

# kenosha scale, ~0.79M params
n_layer = 4
n_head = 4
n_embd = 128
dropout = 0.2

learning_rate = 1e-3
max_iters = 12000
lr_decay_iters = 12000
min_lr = 1e-4
beta2 = 0.99
warmup_iters = 100

seed = 1337

# --- Mac (Apple Silicon) ---
device = 'mps'
compile = False
