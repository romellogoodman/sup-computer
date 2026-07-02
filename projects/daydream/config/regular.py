# Hyperparameters for daydream-chess-nanogpt-1 (Regular, 8x8) -- a char-level
# model on the shared core engine, tokenized over UCI chess moves instead of
# English text.
#
# Corpus: ~15k Lichess games, players rated ~1400-1800 Elo (mid-band on
# purpose -- strong enough for coherent positional shape, loose enough for
# the near-miss dream texture; see the daydream design plan). Small on
# purpose, same ethos as kenosha-kid: this is a hobby-scale art project, not
# an attempt at engine strength.
#
# Run from the repo root:
#   uv run python core/nanogpt_core/train.py \
#       projects/daydream/config/regular.py \
#       --out_dir=projects/daydream/runs/regular-r1

out_dir = 'projects/daydream/runs/regular-r1'
data_root = 'projects/daydream/data/regular'
dataset = 'tokenized'

eval_interval = 100
eval_iters = 100
log_interval = 20

always_save_checkpoint = True
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 256   # holds several full moves of context; games run ~150-400 chars

n_layer = 6
n_head = 6
n_embd = 192
dropout = 0.1

learning_rate = 3e-4
max_iters = 3000
lr_decay_iters = 3000
min_lr = 3e-5
beta2 = 0.99
warmup_iters = 100

# --- Mac (Apple Silicon) ---
device = 'mps'
compile = False
