# pointing, the 2.66M arm -- daydream-Regular shape (6L/6H/192E), the body
# pona used. Char-level pairs `words|slots`, shuffled; 8.27M train tokens, so
# 6000 iters * 16,384 tok/iter is about 12 epochs.
#
# Frozen release copy -- run in place. train_curve.py is what produced the
# release (segments, a snapshot at each step of the curve); train.py config.py
# runs the same recipe in one pass:
#   python train_curve.py        # or: python train.py config.py

out_dir = '.'
data_root = '.'
dataset = 'tokenized'

eval_interval = 250
eval_iters = 50
log_interval = 50

always_save_checkpoint = True   # every eval is a snapshot; the curve is the report
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 256   # 0.77% of units were too long for it and were dropped

n_layer = 6
n_head = 6
n_embd = 192
dropout = 0.1

learning_rate = 1e-3
max_iters = 6000
lr_decay_iters = 6000
min_lr = 1e-4
beta2 = 0.99
warmup_iters = 100

device = 'mps'
compile = False
