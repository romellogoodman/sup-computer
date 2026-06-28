"""Sample from a modern-architecture checkpoint (aliases model_modern as `model`
so the repo's sample.py works unchanged). Same args as sample.py."""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "research-lab"))
os.chdir(REPO)

import model_modern
sys.modules["model"] = model_modern

exec(open(os.path.join(REPO, "research-lab", "sample.py")).read())
