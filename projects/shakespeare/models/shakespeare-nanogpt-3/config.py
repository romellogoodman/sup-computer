# Hyperparameters for shakespeare-nanogpt-3 — the r6 float32 winner:
# modern architecture (RoPE + RMSNorm + bias-free) + a 1024-vocab, byte-level
# BPE trained on the ENLARGED early-modern-drama corpus (Shakespeare's Complete
# Works + Marlowe/Jonson/Kyd/Webster/Dekker), trained at dtype=float32.
#
# Frozen snapshot of the exact settings that produced v3. Originally run on the
# shared core engine as r6-fp32-bpe1k:
#   uv run python core/nanogpt_core/train.py \
#       projects/shakespeare/config/train_shakespeare_mac.py \
#       --dataset=shakespeare_xl_bpe1k \
#       --data_root=projects/shakespeare/data \
#       --dtype=float32 --out_dir=projects/shakespeare/runs/r6-fp32-bpe1k
# train.py auto-loads this file, so `python train.py` (no args) reproduces v3.
# The modern GPT (RoPE + RMSNorm + bias-free) lives in this folder's model.py;
# the 1024-token tokenizer is pinned in shakespeare_xl_bpe1k/tokenizer.json.

out_dir = '.'          # checkpoint (ckpt.pt) is written into this folder
data_root = '.'        # <dataset>/{train,val}.bin + meta.pkl live in ./shakespeare_xl_bpe1k
dataset = 'shakespeare_xl_bpe1k'

eval_interval = 500    # enlarged corpus -> evaluate less often than the tiny baseline
eval_iters = 200
log_interval = 10

# save only when val loss improves -> the released checkpoint is the best-val one
always_save_checkpoint = False

wandb_log = False

gradient_accumulation_steps = 1
batch_size = 64
block_size = 256

# same dims as the char baseline; the small 1024-token vocab keeps this to
# ~11.02M params — about 1/3 of v2's 29.9M GPT-2-vocab model
n_layer = 6
n_head = 6
n_embd = 384
dropout = 0.2
bias = False           # modern, bias-free (RoPE + RMSNorm, see model.py)

learning_rate = 1e-3
max_iters = 2000
lr_decay_iters = 2000
min_lr = 1e-4
beta2 = 0.99
warmup_iters = 100

# float32 is the whole point of r6: it eliminates the MPS float16 large-vocab
# logit overflow that forced r5 to a lower LR, so lr=1e-3 trains cleanly here.
dtype = 'float32'

# --- the Mac-specific bits ---
device = 'mps'
compile = False
