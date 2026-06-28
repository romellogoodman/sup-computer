"""
BPE version of the full Shakespeare corpus for the LLM-assisted research tokenization round.

Identical corpus and identical held-out test slice as data/shakespeare_full, but
encoded with GPT-2 byte-pair encoding instead of characters. No meta.pkl is
written, so the model/eval fall back to the tiktoken GPT-2 tokenizer.

Comparison is done in bits-per-character (research-lab/eval.py), which is tokenizer-
agnostic, so char-level and BPE models are directly comparable.
"""
import os
import urllib.request
import numpy as np
import tiktoken

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

# identical cleaning + slicing as data/shakespeare_full/prepare.py
raw_path = os.path.join(REPO, "data", "shakespeare_full", "raw.txt")
if not os.path.exists(raw_path):
    print("downloading Complete Works of Shakespeare (Project Gutenberg #100)...")
    urllib.request.urlretrieve("https://www.gutenberg.org/cache/epub/100/pg100.txt", raw_path)

raw = open(raw_path, encoding="utf-8").read()
s = raw.find("*** START OF THE PROJECT GUTENBERG")
s = raw.find("\n", s) + 1
e = raw.find("*** END OF THE PROJECT GUTENBERG")
body = raw[s:e].replace("\r\n", "\n").replace("\r", "\n").strip("\n")

TEST_LEN = 250_000
p = int(len(body) * 0.45)
pool = body[:p] + body[p + TEST_LEN :]  # held-out test removed
VAL_LEN = 150_000
val = pool[-VAL_LEN:]
train_full = pool[:-VAL_LEN]

enc = tiktoken.get_encoding("gpt2")
train_ids = enc.encode_ordinary(train_full)
val_ids = enc.encode_ordinary(val)
print(f"train: {len(train_full):,} chars -> {len(train_ids):,} BPE tokens")
print(f"val:   {len(val):,} chars -> {len(val_ids):,} BPE tokens")
print(f"compression: {len(train_full)/len(train_ids):.2f} chars/token")

np.array(train_ids, dtype=np.uint16).tofile(os.path.join(HERE, "train.bin"))
np.array(val_ids, dtype=np.uint16).tofile(os.path.join(HERE, "val.bin"))
print("wrote data/shakespeare_full_bpe/{train,val}.bin (no meta.pkl -> GPT-2 BPE)")
