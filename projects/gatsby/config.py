# Hyperparameters for gatsby-nanogpt on the shared **core** engine (BPE edition).
#
# Gatsby has migrated off its vendored base char-level engine onto core's modern
# arch (RoPE, RMSNorm, bias-free) with byte-level BPE tokenization — see
# docs/adr/0023 and prepare.py. Dims are held IDENTICAL to the released
# gatsby-nanogpt-2 (the char baseline) so any behaviour change is attributable to
# the tokenizer+engine switch alone, not to a resize.
#
# Run from the repo root:
#   uv run python projects/gatsby/prepare.py                       # build data/gatsby_bpe/
#   uv run python core/nanogpt_core/train.py projects/gatsby/config.py \
#       --out_dir=projects/gatsby/runs/migrate-bpe-r1

out_dir = 'projects/gatsby/runs/migrate-bpe-r1'
data_root = 'projects/gatsby/data'   # prepare.py writes <dataset>/*.bin here
dataset = 'gatsby_bpe'               # meta.pkl carries {vocab_size, tokenizer}

eval_interval = 250   # evaluate val loss this often
eval_iters = 200
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
max_iters = 3000
lr_decay_iters = 3000  # usually equal to max_iters
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
