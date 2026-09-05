"""End-to-end test for `sup-train` (nanogpt_core.train_corpus).

Runs the entry point the way a user does — a text file in, a run dir out —
on a small synthetic corpus at the tiny preset, CPU only, well under a
minute. The char path exercises every step (prepare, train, sample, export,
card stub); the bpe path runs only when the `tokenizers` library is
installed.

Run:  uv run --group dev pytest core/tests/
"""

import json
import os
import pickle
import random
import subprocess
import sys

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# the console script uv installs beside the venv's python; the module is the
# fallback so the test also runs from a bare `pip install -e core`
SCRIPT = os.path.join(os.path.dirname(sys.executable), "sup-train")
ENTRY = [SCRIPT] if os.path.exists(SCRIPT) else [sys.executable, "-m", "nanogpt_core.train_corpus"]

QUICK = ["--size", "tiny", "--iters", "20", "--device", "cpu"]
SEPARATOR = "---------------"


def synthetic_corpus(path, words=12_000, seed=0):
    """Varied enough that a BPE can't collapse it into a handful of tokens (a
    repeated sentence would), small enough to train in seconds."""
    rng = random.Random(seed)
    lexicon = [c + v + c2 for c in "bdfgklmnprst" for v in "aeiou" for c2 in "nrst"]  # 240 words
    lines, line = [], []
    for _ in range(words):
        line.append(rng.choice(lexicon))
        if len(line) == 10:
            lines.append(" ".join(line) + ".")
            line = []
    with open(path, "w", encoding="utf-8") as f:
        f.write("Once upon a time, in a lexicon of two hundred forty words:\n" + "\n".join(lines) + "\n")
    return path


def run_sup_train(corpus, out, *extra):
    proc = subprocess.run(
        [*ENTRY, str(corpus), "--out", str(out), *QUICK, *extra],
        cwd=REPO, capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"sup-train failed:\n{proc.stdout}\n{proc.stderr}"
    return proc.stdout


def vocab_size_of(out):
    with open(out / "data" / "corpus" / "meta.pkl", "rb") as f:
        return pickle.load(f)["vocab_size"]


@pytest.fixture(scope="module")
def char_run(tmp_path_factory):
    """One char-level run shared by the tests below."""
    root = tmp_path_factory.mktemp("sup-train")
    corpus = synthetic_corpus(root / "fable.txt")
    out = root / "run"
    stdout = run_sup_train(corpus, out, "--name", "fable")
    return out, stdout


def test_run_dir_has_every_artifact(char_run):
    out, stdout = char_run
    for rel in (
        "data/corpus/train.bin", "data/corpus/val.bin", "data/corpus/meta.pkl",
        "ckpt.pt", "config.py", "model.py", "samples.txt",
        "dist/fable.onnx", "dist/fable.int8.onnx", "dist/fable.vocab.json", "dist/fable.manifest.json",
        "MODEL_CARD.md",
    ):
        assert (out / rel).exists(), f"missing {rel}"
    assert "parity ok" in stdout, "the ONNX parity check did not pass"
    assert "int8 parity" in stdout


def test_samples_and_card_carry_the_run(char_run):
    out, _ = char_run
    samples = (out / "samples.txt").read_text(encoding="utf-8")
    assert samples.count(SEPARATOR) == 2, "expected three samples"
    assert samples.startswith("Once upon a time"), "samples should continue the corpus's first line"

    vocab = vocab_size_of(out)
    card = (out / "MODEL_CARD.md").read_text(encoding="utf-8")
    assert "# Model Card — `fable`" in card
    assert f"| vocab size | {vocab} (char) |" in card
    assert '"vocab_size": %d' % vocab in card, "the registry snippet should carry the vocab size"
    assert "TODO" in card, "human-only sections are marked"

    manifest = json.loads((out / "dist" / "fable.manifest.json").read_text(encoding="utf-8"))
    assert manifest["fable"]["config"]["vocab_size"] == vocab
    assert manifest["fable"]["tokenizer"] == {"type": "char", "vocab": "fable.vocab.json"}


def test_config_reproduces_by_hand(char_run):
    # config.py is what train.py exec'd — the knobs must be the resolved ones
    out, _ = char_run
    ns = {}
    exec((out / "config.py").read_text(encoding="utf-8"), ns)
    assert (ns["n_layer"], ns["n_head"], ns["n_embd"], ns["block_size"]) == (4, 4, 128, 128)
    assert ns["max_iters"] == 20 and ns["device"] == "cpu" and ns["always_save_checkpoint"] is False
    assert ns["out_dir"] == str(out) and ns["dataset"] == "corpus"


def test_bpe_tokenizer(tmp_path):
    pytest.importorskip("tokenizers")
    corpus = synthetic_corpus(tmp_path / "fable.txt")
    out = tmp_path / "run"
    run_sup_train(corpus, out, "--tokenizer", "bpe")

    with open(out / "data" / "corpus" / "meta.pkl", "rb") as f:
        meta = pickle.load(f)
    assert meta["tokenizer"] == "tokenizer.json" and 256 < meta["vocab_size"] <= 1024
    assert (out / "data" / "corpus" / "tokenizer.json").exists()
    assert (out / "dist" / "fable.onnx").exists()
    assert (out / "dist" / "fable.tokenizer.json").exists(), "corpus-BPE runs ship the HF tokenizer sidecar"
    manifest = json.loads((out / "dist" / "fable.manifest.json").read_text(encoding="utf-8"))
    assert manifest["fable"]["tokenizer"] == {"type": "bpe", "tokenizer": "fable.tokenizer.json"}
    card = (out / "MODEL_CARD.md").read_text(encoding="utf-8")
    assert f"| vocab size | {meta['vocab_size']} (bpe) |" in card
