"""
Sample from the frozen checkpoint. Vendored from nanogpt_core/sample.py with
one deliberate change: this is a word-arm model, so decoding goes through
pona_tok.detok — the shared engine's raw token join is wrong for this vocab
(see projects/pona/CLAUDE.md, "two arms, two tokenizers").

Usage (in place):
  python sample.py --num_samples=3 --max_new_tokens=60
"""
import os
import pickle
from contextlib import nullcontext

import torch

from checkpoint import load_model, pick_device  # vendored: no cross-folder imports
import pona_tok

# -----------------------------------------------------------------------------
out_dir = '.' # directory holding ckpt.pt
start = "\n"
num_samples = 10 # number of samples to draw
max_new_tokens = 100 # word tokens per sample (~6 words per sentence)
temperature = 0.8
top_k = 200
seed = 1337
device = '' # '' auto-picks (cuda > mps > cpu); or 'cpu', 'cuda', 'mps', ...
dtype = 'bfloat16' if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else 'float32'
compile = False
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'configurator.py')).read()) # cmdline/config overrides (location-independent)
# -----------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))

device = pick_device(device or None)
torch.manual_seed(seed)
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
device_type = 'cuda' if 'cuda' in device else 'mps' if 'mps' in device else 'cpu'
ptdtype = {'float32': torch.float32, 'bfloat16': torch.bfloat16, 'float16': torch.float16}[dtype]
ctx = nullcontext() if device_type == 'cpu' else torch.amp.autocast(device_type=device_type, dtype=ptdtype)

model, checkpoint = load_model(out_dir, device)
if compile:
    model = torch.compile(model)

# the word vocab ships with the snapshot; the ckpt's recorded data_root is the
# repo-root path it was trained under, so fall back to the local copy
dataset = checkpoint["config"]["dataset"]
meta_path = os.path.join(checkpoint["config"]["data_root"], dataset, "meta.pkl")
if not os.path.exists(meta_path):
    meta_path = os.path.join(HERE, dataset, "meta.pkl")
with open(meta_path, "rb") as f:
    meta = pickle.load(f)
stoi, itos = meta["stoi"], meta["itos"]

start_ids = pona_tok.encode(start, stoi)
x = (torch.tensor(start_ids, dtype=torch.long, device=device)[None, ...])

with torch.no_grad():
    with ctx:
        for k in range(num_samples):
            y = model.generate(x, max_new_tokens, temperature=temperature, top_k=top_k)
            print(pona_tok.detok([itos[i] for i in y[0].tolist()]))
            print('---------------')
