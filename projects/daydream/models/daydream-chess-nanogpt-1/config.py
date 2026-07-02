# Hyperparameters for daydream-chess-nanogpt-1 (Regular, 8x8) — the
# CHAMPION recipe, frozen.
#
# This is the self-contained release copy. Every path resolves relative to
# THIS folder, so `python train.py config.py` run from inside the snapshot
# reproduces the released checkpoint with no dependency on the project root
# or shared core.
#
# Corpus: ~4,135 Lichess games, players rated ~1400-1800 Elo (mid-band on
# purpose — strong enough for coherent positional shape, loose enough for
# the near-miss dream texture). Small on purpose, same ethos as
# kenosha-kid: this is a hobby-scale art project, not an attempt at engine
# strength.
#
# Run from inside this folder:
#   python fetch_filtered.py   # -> games.txt (needs network; Lichess dump)
#   python prepare.py          # -> regular/{train,val}.bin + meta.pkl
#   python train.py config.py

out_dir = '.'          # checkpoint (ckpt.pt) is written into this folder
data_root = '.'        # <dataset>/*.bin + meta.pkl live in ./regular (prepare.py)
dataset = 'regular'

eval_interval = 100
eval_iters = 100
log_interval = 20

always_save_checkpoint = True
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 256

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
