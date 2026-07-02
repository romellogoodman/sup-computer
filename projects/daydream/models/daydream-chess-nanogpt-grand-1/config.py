# Hyperparameters for daydream-chess-nanogpt-grand-1 (12 files x 10 ranks,
# Chancellor + Archbishop) -- the CHAMPION recipe, frozen. Every path
# resolves relative to THIS folder.
#
# Corpus: Fairy-Stockfish self-play under the custom `grand12` variant
# (vendored here as variants.ini) -- no human corpus exists for this board.
# games.txt is vendored here (synthetic, seeded, code-owned).
#
# Run from inside this folder:
#   python prepare.py          # -> grand/{train,val}.bin + meta.pkl
#   python train.py config.py

out_dir = '.'
data_root = '.'
dataset = 'grand'

eval_interval = 100
eval_iters = 100
log_interval = 20

always_save_checkpoint = True
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 48
block_size = 512

n_layer = 6
n_head = 8
n_embd = 256
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
