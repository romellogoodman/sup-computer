# Hyperparameters for shakespeare-nanogpt-1 (the base char-level model).
#
# This is the frozen snapshot of research-lab/config/train_shakespeare_mac.py as it produced
# v1. train.py auto-loads this file, so `python train.py` (no args) reproduces
# the model; override any knob with e.g. `--max_iters=5000`.

out_dir = '.'         # checkpoint (ckpt.pt) is written into this folder
eval_interval = 250   # evaluate val loss this often (we overfit fast on tiny data)
eval_iters = 200
log_interval = 10     # print training loss this often

# small dataset -> we expect to overfit, so only checkpoint when val loss improves
always_save_checkpoint = False

wandb_log = False     # no experiment tracking

dataset = 'shakespeare_char'   # recorded in the checkpoint; data is read from this folder
gradient_accumulation_steps = 1
batch_size = 64
block_size = 256      # context length: predict char N+1 from the previous 256 chars

# the "baby GPT" — ~10.6M parameters
n_layer = 6
n_head = 6
n_embd = 384
dropout = 0.2

learning_rate = 1e-3  # small networks can use a higher LR
max_iters = 2000      # ~10 min on an M-series Mac; bump to 5000 for noticeably better text
lr_decay_iters = 2000 # usually equal to max_iters
min_lr = 1e-4
beta2 = 0.99          # a bit higher because we see few tokens per step
warmup_iters = 100

# --- the Mac-specific bits ---
device = 'mps'        # Apple Metal GPU. Use 'cpu' if you hit MPS issues.
compile = False       # torch.compile is unreliable on macOS / MPS
