# Hyperparameters for glyph-nanogpt-1 (omni-xl, the letter-conditioned
# generalist) — the released recipe, frozen.
#
# This is the self-contained release copy. Every path resolves relative to
# THIS folder, so running the pipeline from inside the snapshot reproduces
# the released checkpoint with no dependency on the project root or the
# shared core.
#
# Corpus: 81,934 lowercase glyph outlines from 759 OFL sans-serif families
# (google/fonts, commit pinned in manifest.json), serialized one char per
# token (ADR-0027). The model is 12L/8H/576E ≈ 47.8M params — the parameter
# SUM of the 26 specialists it was measured against (experiment 09).
#
# The optimizer is deliberately NOT the small-model recipe: lr 3e-4 /
# beta2 0.99 diverged three times at this scale (healthy to ~step 600, then
# the loss exploded, grad_clip active). lr 1e-4 / beta2 0.95 / warmup 300
# is the standard big-model adjustment that held.
#
# Run from inside this folder:
#   python fetch_fonts.py      # -> gfonts/ + manifest.json (needs network)
#   python encode_corpus.py    # -> corpus/<letter>.txt
#   python prepare.py          # -> omni/{train,val}.bin + meta.pkl (and the
#                              #    per-letter datasets + test/ files)
#   python train.py config.py

out_dir = '.'          # checkpoint (ckpt.pt) is written into this folder
data_root = '.'        # prepare.py writes ./omni/{train,val}.bin + meta.pkl
dataset = 'omni'

eval_interval = 100
eval_iters = 50
log_interval = 20

always_save_checkpoint = False   # keep best-val, not last
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
