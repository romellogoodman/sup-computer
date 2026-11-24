# Lucky control: Maryland Pick 3, no history (unreleased).
#
# Reads nothing, predicts one draw at a time. The twin the history version is measured against.
#
# Run from the repo root:
#   uv run python projects/lucky/train.py projects/lucky/config/lucky_control.py

out_dir = 'projects/lucky/runs/lucky-control'
data_root = 'projects/lucky/data/pick3'
dataset = 'tokenized'
game = 'pick3'
history = 0        # draws of context; block_size = (history + 1) * 4 = 4

eval_interval = 100
log_interval = 50
batch_size = 256       # about 82 steps per epoch
max_iters = 3000

# the same body for all four runs, so the only differences are the game and the history
n_layer = 4
n_head = 4
n_embd = 128
dropout = 0.0

learning_rate = 3e-4
warmup_iters = 100
lr_decay_iters = 3000
min_lr = 3e-5
beta2 = 0.99
weight_decay = 1e-1

seed = 1337
