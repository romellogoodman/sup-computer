# Pilot hyperparameters for the glyph specialists (a, e, g) AND omni-aeg --
# one config so the arms differ in nothing but their dataset. The pilot's
# job is to settle this config; the 26-letter matrix inherits what survives.
#
# Small corpus, so the anti-memorization posture is baked in: dropout 0.2,
# and always_save_checkpoint=False keeps the BEST-val checkpoint, not the
# last one -- a run that starts memorizing keeps its pre-overfit weights.
#
# Run from the repo root (override dataset/out_dir per model):
#   uv run python core/nanogpt_core/train.py \
#       projects/glyph/config/specialist_pilot.py \
#       --dataset=a --out_dir=projects/glyph/runs/pilot-a-r1

out_dir = 'projects/glyph/runs/pilot-a-r1'
data_root = 'projects/glyph/data'
dataset = 'a'

eval_interval = 100
eval_iters = 50
log_interval = 20

always_save_checkpoint = False   # keep best-val, not last (memorization guard)
wandb_log = False

gradient_accumulation_steps = 1
batch_size = 32
block_size = 512   # p99 glyph is 275 tokens; every whole glyph fits

n_layer = 4
n_head = 4
n_embd = 192
dropout = 0.2

learning_rate = 3e-4
max_iters = 2000
lr_decay_iters = 2000
min_lr = 3e-5
beta2 = 0.99
warmup_iters = 100

# --- Mac (Apple Silicon) ---
device = 'mps'
compile = False
