# pointing, the 0.79M arm -- kenosha-kid shape (4L/4H/128E). Everything else
# is the regular arm, line for line: same pairs, same block, same schedule.
#
# Run from the repo root:
#   uv run python projects/pointing/train_curve.py projects/pointing/config/small.py

out_dir = 'projects/pointing/runs/small-r1'
data_root = 'projects/pointing/data'
dataset = 'tokenized'

eval_interval = 250
eval_iters = 50
log_interval = 50

always_save_checkpoint = True   # every eval is a snapshot; the curve is the report
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 256   # 0.77% of units were too long for it and were dropped

n_layer = 4
n_head = 4
n_embd = 128
dropout = 0.1

learning_rate = 1e-3
max_iters = 6000
lr_decay_iters = 6000
min_lr = 1e-4
beta2 = 0.99
warmup_iters = 100

device = 'mps'
compile = False
