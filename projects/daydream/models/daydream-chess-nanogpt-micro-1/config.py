# Hyperparameters for daydream-chess-nanogpt-micro-1 (Gardner 5x5) — the
# CHAMPION recipe, frozen. Every path resolves relative to THIS folder.
#
# Corpus: Fairy-Stockfish self-play under the built-in `gardner` variant —
# no human corpus exists for a 5x5 board. games.txt is vendored here
# (synthetic, seeded, code-owned — same treatment as kenosha-kid's raw.txt).
#
# Run from inside this folder:
#   python prepare.py          # -> micro/{train,val}.bin + meta.pkl
#   python train.py config.py

out_dir = '.'
data_root = '.'
dataset = 'micro'

eval_interval = 100
eval_iters = 100
log_interval = 20

always_save_checkpoint = True
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 128

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
