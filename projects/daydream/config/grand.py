# Hyperparameters for daydream-chess-nanogpt-grand-1 (12 files x 10 ranks,
# Chancellor + Archbishop).
#
# Corpus: Fairy-Stockfish self-play under the custom `grand12` variant --
# no human corpus exists for this board. Largest tier, largest vocab
# (extra promotion letters for Chancellor/Archbishop, file letters through
# 'l'), longest games observed in self-play (~100-130 plies) -- more
# capacity and a longer context window than Micro/Regular.
#
# Run from the repo root:
#   uv run python core/nanogpt_core/train.py \
#       projects/daydream/config/grand.py \
#       --out_dir=projects/daydream/runs/grand-r1

out_dir = 'projects/daydream/runs/grand-r1'
data_root = 'projects/daydream/data/grand'
dataset = 'tokenized'

eval_interval = 100
eval_iters = 100
log_interval = 20

always_save_checkpoint = True
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 48
block_size = 512   # longer games than Regular/Micro -- more moves of context

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
