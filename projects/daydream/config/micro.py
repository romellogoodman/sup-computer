# Hyperparameters for daydream-chess-nanogpt-micro-1 (Gardner 5x5).
#
# Corpus: Fairy-Stockfish self-play under the built-in `gardner` variant --
# no human corpus exists for a 5x5 board. Smallest tier, smallest board,
# smallest vocab -- capacity scaled down to match, same "small on purpose"
# ethos as kenosha-kid.
#
# Run from the repo root:
#   uv run python core/nanogpt_core/train.py \
#       projects/daydream/config/micro.py \
#       --out_dir=projects/daydream/runs/micro-r1

out_dir = 'projects/daydream/runs/micro-r1'
data_root = 'projects/daydream/data/micro'
dataset = 'tokenized'

eval_interval = 100
eval_iters = 100
log_interval = 20

always_save_checkpoint = True
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 128   # Gardner games run short (~20-40 plies observed in self-play)

n_layer = 4
n_head = 4
n_embd = 128
dropout = 0.1

learning_rate = 3e-4
max_iters = 2500
lr_decay_iters = 2500
min_lr = 3e-5
beta2 = 0.99
warmup_iters = 100

# --- Mac (Apple Silicon) ---
device = 'mps'
compile = False
