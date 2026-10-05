# gatsby-nanogpt-3 — the exact released hyperparameters (frozen copy of
# projects/gatsby/config/v3.py as the sweep's v3-full run used it).
#
# Run in place:   python prepare.py && python train.py
#
# `subset` names the training subset of tiny-green-light-stories v3 that
# prepare.py downloads from Hugging Face (v3/subsets/<subset>.json).
subset = 'train-full'

out_dir = '.'
data_root = '.'
dataset = 'data'                     # prepare.py writes data/{train,val}.bin + meta.pkl

eval_interval = 250   # evaluate val loss this often
eval_iters = 50     # val.bin is ~0.5M tokens; 50 x 64 x 256 samples it well
log_interval = 10     # print training loss this often

# synthetic corpus is small-ish -> only checkpoint when val loss improves
always_save_checkpoint = False

wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
# BPE compresses the corpus ~3-4x, so a whole story (~500-1100 chars) plus its
# [green=N] topic: ... control line fits in ~150-256 tokens. 256 keeps the
# control line and the story body in one window, so the conditioned obsession +
# topic stay in view across the document.
block_size = 256

# the "baby GPT" — same shape as gatsby-nanogpt-2 (n_embd/n_layer/n_head fixed
# for comparability; param count shifts only with the BPE vocab vs char vocab,
# and RoPE drops the learned wpe table entirely).
n_layer = 6
n_head = 6
n_embd = 384
dropout = 0.2

learning_rate = 1e-3  # small networks can use a higher LR
max_iters = 8000
lr_decay_iters = 8000  # usually equal to max_iters
min_lr = 1e-4
beta2 = 0.99          # a bit higher because we see few tokens per step
warmup_iters = 100

# --- the Mac-specific bits ---
device = 'mps'        # Apple Metal GPU
compile = False       # torch.compile is unreliable on macOS / MPS
# float32, NOT float16: core's GradScaler is CUDA-only, so MPS float16 autocast
# runs unscaled and large logits overflow (this diverged shakespeare's large-vocab
# BPE run). gatsby is small; float32 on MPS is plenty fast and sidesteps it.
dtype = 'float32'
