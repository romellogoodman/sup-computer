"""
Sample from a trained gatsby-nanogpt model.

The model was trained on documents of the form:

    [green=N] [green=N] [green=N] obsession=<word>
    topic: <a topic>
    <a TinyStories-register story, fixated on a green light at intensity N>

So to drive it, prime it with a control line and let it continue. Example:

    python sample.py --start="[green=5] [green=5] [green=5] obsession=total
topic: a dog and a balloon
" --num_samples=1 --max_new_tokens=600

The web-ui builds this prime for you (topic box + green-light dial). Pass
arbitrary operator text safely via a file with --start="FILE:prompt.txt".
"""
import os
import pickle
from contextlib import nullcontext
import torch
from model import GPTConfig, GPT

# Run from this folder so the checkpoint and meta.pkl resolve locally.
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

# -----------------------------------------------------------------------------
init_from = 'resume'  # 'resume' (from out_dir) or a gpt2 variant
out_dir = '.'         # this folder holds ckpt.pt
start = "[green=5] [green=5] [green=5] obsession=total\ntopic: a lost kitten\n"  # prompt; or "FILE:prompt.txt"
num_samples = 5       # number of samples to draw
max_new_tokens = 600  # number of tokens generated in each sample
temperature = 0.8     # 1.0 = no change, < 1.0 = less random, > 1.0 = more random
top_k = 200           # retain only the top_k most likely tokens
seed = 1337
device = 'mps'        # Apple Metal GPU; use 'cpu' if MPS misbehaves (or 'cuda' on NVIDIA)
dtype = 'float16'
compile = False
exec(open('configurator.py').read())  # overrides from command line or config file
# -----------------------------------------------------------------------------

torch.manual_seed(seed)
torch.cuda.manual_seed(seed)
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
device_type = 'cuda' if 'cuda' in device else 'cpu'
ptdtype = {'float32': torch.float32, 'bfloat16': torch.bfloat16, 'float16': torch.float16}[dtype]
ctx = nullcontext() if device_type == 'cpu' else torch.amp.autocast(device_type=device_type, dtype=ptdtype)

# model
ckpt_path = os.path.join(out_dir, 'ckpt.pt')
checkpoint = torch.load(ckpt_path, map_location=device)
gptconf = GPTConfig(**checkpoint['model_args'])
model = GPT(gptconf)
state_dict = checkpoint['model']
unwanted_prefix = '_orig_mod.'
for k, v in list(state_dict.items()):
    if k.startswith(unwanted_prefix):
        state_dict[k[len(unwanted_prefix):]] = state_dict.pop(k)
model.load_state_dict(state_dict)

model.eval()
model.to(device)
if compile:
    model = torch.compile(model)

# char-level encode/decode from meta.pkl
meta_path = os.path.join(HERE, 'meta.pkl')
with open(meta_path, 'rb') as f:
    meta = pickle.load(f)
stoi, itos = meta['stoi'], meta['itos']
# drop any chars not in the vocab so arbitrary operator input can't crash the encoder
encode = lambda s: [stoi[c] for c in s if c in stoi]
decode = lambda l: ''.join([itos[i] for i in l])

# encode the prompt
if start.startswith('FILE:'):
    with open(start[5:], 'r', encoding='utf-8') as f:
        start = f.read()
start_ids = encode(start)
if not start_ids:
    start_ids = encode("\n")  # model needs at least one token
x = (torch.tensor(start_ids, dtype=torch.long, device=device)[None, ...])

# run generation
with torch.no_grad():
    with ctx:
        for k in range(num_samples):
            y = model.generate(x, max_new_tokens, temperature=temperature, top_k=top_k)
            print(decode(y[0].tolist()))
            print('---------------')
