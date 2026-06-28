# Hyperparameters for shakespeare-nanogpt-2 (the research-lab Round 3 winner:
# modern architecture + GPT-2 BPE on the full Complete Works).
#
# Frozen snapshot of the exact settings that produced v2, originally run as:
#   research-lab/train_modern.py research-lab/config/train_shakespeare_mac.py \
#     --dataset=shakespeare_full_bpe --out_dir=.../r3-bpe --bias=False --eval_interval=500
# train.py auto-loads this file, so `python train.py` (no args) reproduces v2.
# The modern GPT (RoPE + RMSNorm + bias-free) lives in this folder's model.py.

out_dir = '.'         # checkpoint (ckpt.pt) is written into this folder
eval_interval = 500   # full corpus -> evaluate less often than the tiny baseline
eval_iters = 200
log_interval = 10

always_save_checkpoint = False

wandb_log = False

dataset = 'shakespeare_full_bpe'   # recorded in the checkpoint; data is read from this folder
gradient_accumulation_steps = 1
batch_size = 64
block_size = 256

# same dims as the baseline; BPE's ~50k vocab embedding makes this ~29.9M params
n_layer = 6
n_head = 6
n_embd = 384
dropout = 0.2
bias = False          # modern, bias-free (RoPE + RMSNorm, see model.py)

learning_rate = 1e-3
max_iters = 2000
lr_decay_iters = 2000
min_lr = 1e-4
beta2 = 0.99
warmup_iters = 100

# --- the Mac-specific bits ---
device = 'mps'
compile = False
