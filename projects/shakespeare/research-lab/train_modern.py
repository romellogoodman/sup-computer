"""
Train the modern GPT variant (research-lab/model_modern.py) using the repo's train.py
unchanged. We alias model_modern as the `model` module so train.py's
`from model import GPTConfig, GPT` picks up the modern architecture, then tag the
output dir so research-lab/eval.py knows which architecture to reconstruct.

Usage (same args as the engine train.py):
  python research-lab/train_modern.py research-lab/config/train_shakespeare_mac.py --dataset=shakespeare_full --out_dir=research-lab/runs/r2-arch-modern --bias=False
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "research-lab"))
os.chdir(REPO)

import model_modern
sys.modules["model"] = model_modern  # redirect train.py's `from model import ...`

exec(open(os.path.join(REPO, "research-lab", "train.py")).read())

# tag the output dir with the architecture so eval reconstructs it correctly
with open(os.path.join(out_dir, "arch.txt"), "w") as f:  # noqa: F821 (from train.py)
    f.write("modern")
