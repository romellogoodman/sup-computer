# pona word arm -- one Toki Pona word = one token (data/pona_tok.py); the
# 368-token vocab IS the keyboard the chat UI renders. Same 6L/6H/192E body as
# the char arm; block 128 words ~= a dozen sentences of context. 1500 iters *
# 8,192 tok/iter ~= 7 epochs of the 1.73M-token corpus -- epoch parity with
# the char arm, which is the controlled part of the span comparison.
#
# Run from the repo root:
#   uv run python core/nanogpt_core/train.py projects/pona/config/word.py

out_dir = 'projects/pona/runs/word-r1'
data_root = 'projects/pona/data'
dataset = 'tokenized-word'

eval_interval = 50
eval_iters = 100
log_interval = 20

always_save_checkpoint = False
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 128

n_layer = 6
n_head = 6
n_embd = 192
dropout = 0.1

learning_rate = 3e-4
max_iters = 1500
lr_decay_iters = 1500
min_lr = 3e-5
beta2 = 0.99
warmup_iters = 50

device = 'mps'
compile = False
