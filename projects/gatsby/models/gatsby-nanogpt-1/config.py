# Hyperparameters for gatsby-nanogpt (the base char-level model).
#
# A "baby GPT" trained on a synthetic TinyStories-register corpus where every
# story is fixated on a green light at a tagged intensity (see generate.py and
# the [green=N] control-line format). train.py auto-loads this file, so
# `python train.py` (no args) reproduces the model; override any knob with e.g.
# `--max_iters=5000`.

out_dir = '.'         # checkpoint (ckpt.pt) is written into this folder
eval_interval = 250   # evaluate val loss this often
eval_iters = 200
log_interval = 10     # print training loss this often

# synthetic corpus is small-ish -> only checkpoint when val loss improves
always_save_checkpoint = False

wandb_log = False     # no experiment tracking

dataset = 'gatsby_char'   # recorded in the checkpoint; data is read from this folder
gradient_accumulation_steps = 1
batch_size = 64
# context length: a whole TinyStories-register story (~700-1100 chars) plus its
# [green=N] topic: ... control line. 512 keeps the control line and most of the
# story in view, so the conditioned obsession stays coherent across the document.
block_size = 512

# the "baby GPT" — ~10.7M parameters (wpe grows slightly vs block_size=256)
n_layer = 6
n_head = 6
n_embd = 384
dropout = 0.2

learning_rate = 1e-3  # small networks can use a higher LR
max_iters = 3000      # ~15-20 min on an M-series Mac at block_size=512
lr_decay_iters = 3000 # usually equal to max_iters
min_lr = 1e-4
beta2 = 0.99          # a bit higher because we see few tokens per step
warmup_iters = 100

# --- the Mac-specific bits ---
device = 'mps'        # Apple Metal GPU. Use 'cpu' if you hit MPS issues.
compile = False       # torch.compile is unreliable on macOS / MPS
