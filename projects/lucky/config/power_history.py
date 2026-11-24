# lucky-nanogpt-power-1 (Lucky Power): Powerball, history version (released).
#
# Reads the last 8 draws, predicts the next one. Whites are reshuffled every epoch.
#
# Run from the repo root:
#   uv run python projects/lucky/train.py projects/lucky/config/power_history.py

out_dir = 'projects/lucky/runs/power-history'
data_root = 'projects/lucky/data/powerball'
dataset = 'tokenized'
game = 'powerball'
history = 8        # draws of context; block_size = (history + 1) * 8 = 72

eval_interval = 100
log_interval = 50
batch_size = 64       # about 18 steps per epoch
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

device = 'cpu'           # four tiny models; CPU keeps them off the shared GPU
