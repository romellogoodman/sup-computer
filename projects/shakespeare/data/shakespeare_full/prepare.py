"""
Prepare the Complete Works of Shakespeare for the LLM-assisted research data experiment.

Builds TWO char-level datasets that share an identical vocabulary, plus one
fixed held-out test set used to score every model fairly:

  data/shakespeare_full/   - train on the full corpus (~5MB)  [treatment]
  data/shakespeare_small/  - train on a 1MB subset (~Tiny size) [control]
  test.txt                 - a held-out slice neither model ever trains on
                             (written to the project root: projects/shakespeare/)

Both conditions are identical except for training-data quantity, so the
difference in held-out loss is the causal effect of data alone.
"""
import os
import pickle
import urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

# download the Complete Works from Project Gutenberg on first run
raw_path = os.path.join(HERE, "raw.txt")
if not os.path.exists(raw_path):
    print("downloading Complete Works of Shakespeare (Project Gutenberg #100)...")
    urllib.request.urlretrieve("https://www.gutenberg.org/cache/epub/100/pg100.txt", raw_path)

raw = open(raw_path, encoding="utf-8").read()

# strip Project Gutenberg header/footer so they don't pollute the data/vocab
s = raw.find("*** START OF THE PROJECT GUTENBERG")
s = raw.find("\n", s) + 1
e = raw.find("*** END OF THE PROJECT GUTENBERG")
body = raw[s:e].replace("\r\n", "\n").replace("\r", "\n").strip("\n")
print(f"clean corpus: {len(body):,} characters")

# shared vocabulary over the WHOLE corpus (so both datasets + the test set
# encode with the same char->int mapping)
chars = sorted(set(body))
vocab_size = len(chars)
stoi = {c: i for i, c in enumerate(chars)}
itos = {i: c for i, c in enumerate(chars)}
encode = lambda t: [stoi[c] for c in t]
print(f"vocab size: {vocab_size}")

# carve a fixed held-out test set (a contiguous block in the middle) and remove
# it from the training pool entirely
TEST_LEN = 250_000
p = int(len(body) * 0.45)
test = body[p : p + TEST_LEN]
pool = body[:p] + body[p + TEST_LEN :]

# in-training validation slice (used only for checkpoint selection)
VAL_LEN = 150_000
val = pool[-VAL_LEN:]
train_full = pool[:-VAL_LEN]
train_small = train_full[:1_000_000]  # control: ~Tiny-Shakespeare-sized subset

print(
    f"test={len(test):,}  val={len(val):,}  "
    f"train_full={len(train_full):,}  train_small={len(train_small):,}"
)


def dump(dirname, train_text):
    d = os.path.join(REPO, "data", dirname)
    os.makedirs(d, exist_ok=True)
    np.array(encode(train_text), dtype=np.uint16).tofile(os.path.join(d, "train.bin"))
    np.array(encode(val), dtype=np.uint16).tofile(os.path.join(d, "val.bin"))
    with open(os.path.join(d, "meta.pkl"), "wb") as f:
        pickle.dump({"vocab_size": vocab_size, "stoi": stoi, "itos": itos}, f)
    print(f"wrote data/{dirname}/")


dump("shakespeare_full", train_full)
dump("shakespeare_small", train_small)

# REPO here is the project root (projects/shakespeare/); the held-out test set
# lives there, next to the runs that are scored against it.
with open(os.path.join(REPO, "test.txt"), "w", encoding="utf-8") as f:
    f.write(test)
print("wrote test.txt (held-out test set)")
