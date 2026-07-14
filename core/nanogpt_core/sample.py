"""
Sample from a trained checkpoint. The tokenizer resolves from the dataset's
meta.pkl (char, corpus-trained HF BPE, or GPT-2 — see nanogpt_core.checkpoint).

Usage (repo root):
  uv run python core/nanogpt_core/sample.py \
      --out_dir=projects/shakespeare/runs/r1 \
      --data_root=projects/shakespeare/data \
      --start="ROMEO:" --num_samples=1 --max_new_tokens=500
"""
import os
from contextlib import nullcontext

import torch

from nanogpt_core.checkpoint import load_model, load_tokenizer, pick_device

# -----------------------------------------------------------------------------
out_dir = 'out' # directory holding ckpt.pt
start = "\n" # or "<|endoftext|>" or etc. Can also specify a file, use as: "FILE:prompt.txt"
num_samples = 10 # number of samples to draw
max_new_tokens = 500 # number of tokens generated in each sample
temperature = 0.8 # 1.0 = no change, < 1.0 = less random, > 1.0 = more random, in predictions
top_k = 200 # retain only the top_k most likely tokens, clamp others to have 0 probability
seed = 1337
device = '' # '' auto-picks (cuda > mps > cpu); or 'cpu', 'cuda', 'mps', ...
dtype = 'bfloat16' if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else 'float32' # autocast dtype
compile = False # use PyTorch 2.0 to compile the model to be faster
data_root = 'data' # parent dir of <dataset>/meta.pkl (char models); override per project
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'configurator.py')).read()) # cmdline/config overrides (location-independent)
# -----------------------------------------------------------------------------

device = pick_device(device or None)
torch.manual_seed(seed) # seeds CPU and all accelerator RNGs
torch.backends.cuda.matmul.allow_tf32 = True # allow tf32 on matmul
torch.backends.cudnn.allow_tf32 = True # allow tf32 on cudnn
device_type = 'cuda' if 'cuda' in device else 'mps' if 'mps' in device else 'cpu' # for later use in torch.autocast
ptdtype = {'float32': torch.float32, 'bfloat16': torch.bfloat16, 'float16': torch.float16}[dtype]
ctx = nullcontext() if device_type == 'cpu' else torch.amp.autocast(device_type=device_type, dtype=ptdtype)

model, checkpoint = load_model(out_dir, device)
if compile:
    model = torch.compile(model) # requires PyTorch 2.0 (optional)

tok = load_tokenizer(checkpoint, data_root)
print(f"tokenizer: {tok.kind}")

# encode the beginning of the prompt
if start.startswith('FILE:'):
    with open(start[5:], 'r', encoding='utf-8') as f:
        start = f.read()
start_ids = tok.encode(start)
x = (torch.tensor(start_ids, dtype=torch.long, device=device)[None, ...])

# run generation
with torch.no_grad():
    with ctx:
        for k in range(num_samples):
            y = model.generate(x, max_new_tokens, temperature=temperature, top_k=top_k)
            print(tok.decode(y[0].tolist()))
            print('---------------')
