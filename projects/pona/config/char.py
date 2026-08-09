# pona char arm -- one character = one token, the studio's usual contract.
# daydream-Regular shape (6L/6H/192E, 2.7M params). Corpus: 6.93M chars of
# filtered Wikipedia + poki + Tatoeba; 3000 iters * 16,384 tok/iter ~= 8 epochs.
#
# Run from the repo root:
#   uv run python core/nanogpt_core/train.py projects/pona/config/char.py

out_dir = 'projects/pona/runs/char-r1'
data_root = 'projects/pona/data'
dataset = 'tokenized-char'

eval_interval = 100
eval_iters = 100
log_interval = 20

always_save_checkpoint = False
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 256   # ~5 sentences of context at ~50 chars/sentence

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

device = 'mps'
compile = False
