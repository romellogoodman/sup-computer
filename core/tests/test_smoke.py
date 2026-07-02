"""End-to-end smoke test for the core engine.

Drives the real scripts the way a researcher does — train from scratch on a
tiny synthetic char corpus, resume, sample, eval, export — so the wiring that
unit tests miss (configurator overrides, checkpoint schema, resume state,
script CLIs) is exercised on every run. CPU-only, ~a minute.

Run:  uv run --group dev pytest core/tests/
"""

import os
import pickle
import subprocess
import sys

import numpy as np
import pytest
import torch

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

TRAIN = os.path.join(REPO, "core", "nanogpt_core", "train.py")
SAMPLE = os.path.join(REPO, "core", "nanogpt_core", "sample.py")
EVAL = os.path.join(REPO, "core", "eval", "eval.py")
EXPORT = os.path.join(REPO, "core", "export", "export.py")

TINY_ARGS = [
    "--device=cpu", "--compile=False", "--dtype=float32",
    "--n_layer=1", "--n_head=2", "--n_embd=32", "--block_size=32",
    "--batch_size=4", "--gradient_accumulation_steps=1",
    "--eval_iters=2", "--log_interval=1", "--always_save_checkpoint=True",
    "--warmup_iters=1", "--dataset=tiny",
]


def run(script, *args, cwd=REPO):
    proc = subprocess.run(
        [sys.executable, script, *args], cwd=cwd, capture_output=True, text=True
    )
    assert proc.returncode == 0, f"{script} failed:\n{proc.stdout}\n{proc.stderr}"
    return proc.stdout


@pytest.fixture(scope="module")
def workdir(tmp_path_factory):
    """A tiny char dataset + a trained-and-resumed checkpoint, shared by tests."""
    root = tmp_path_factory.mktemp("smoke")
    data_dir = root / "data" / "tiny"
    data_dir.mkdir(parents=True)

    text = "the quick brown fox jumps over the lazy dog. " * 200
    chars = sorted(set(text))
    stoi = {c: i for i, c in enumerate(chars)}
    itos = {i: c for i, c in enumerate(chars)}
    ids = np.array([stoi[c] for c in text], dtype=np.uint16)
    ids[: int(len(ids) * 0.9)].tofile(data_dir / "train.bin")
    ids[int(len(ids) * 0.9):].tofile(data_dir / "val.bin")
    with open(data_dir / "meta.pkl", "wb") as f:
        pickle.dump({"vocab_size": len(chars), "stoi": stoi, "itos": itos}, f)
    (root / "test.txt").write_text(text[:500], encoding="utf-8")

    out_dir = root / "out"
    common = [f"--data_root={root / 'data'}", f"--out_dir={out_dir}", *TINY_ARGS]
    run(TRAIN, *common, "--init_from=scratch",
        "--max_iters=5", "--eval_interval=5", "--lr_decay_iters=5")
    assert (out_dir / "ckpt.pt").exists(), "training produced no checkpoint"

    # resume must pick up where it left off, not restart
    out = run(TRAIN, *common, "--init_from=resume",
              "--max_iters=8", "--eval_interval=3", "--lr_decay_iters=8")
    assert "iter 6:" in out and "iter 0:" not in out, "resume restarted from iter 0"
    return root


def test_checkpoint_carries_resume_state(workdir):
    ckpt = torch.load(workdir / "out" / "ckpt.pt", map_location="cpu", weights_only=True)
    for key in ("model", "optimizer", "model_args", "iter_num", "config",
                "scaler", "rng_state"):
        assert key in ckpt, f"checkpoint missing {key!r}"
    assert ckpt["iter_num"] > 5


def test_sample_generates_text(workdir):
    out = run(SAMPLE, f"--out_dir={workdir / 'out'}", f"--data_root={workdir / 'data'}",
              "--device=cpu", "--dtype=float32", "--compile=False",
              "--num_samples=1", "--max_new_tokens=20", "--start=the")
    assert "---------------" in out, "sample.py produced no sample"


def test_eval_reports_bpc(workdir):
    out = run(EVAL, str(workdir / "out"),
              "--test", str(workdir / "test.txt"),
              "--data-dir", str(workdir / "data"))
    assert "BPC=" in out and "tokenizer=char" in out


def test_export_parity(workdir, tmp_path):
    pytest.importorskip("onnx")
    pytest.importorskip("onnxruntime")
    # export expects a frozen version folder: model.py + ckpt.pt side by side
    folder = tmp_path / "tiny-model"
    folder.mkdir()
    (folder / "model.py").write_bytes(
        open(os.path.join(REPO, "core", "nanogpt_core", "model.py"), "rb").read()
    )
    (folder / "ckpt.pt").write_bytes(open(workdir / "out" / "ckpt.pt", "rb").read())
    out = run(EXPORT, str(folder), str(tmp_path / "dist"))
    assert "parity ok" in out, "fp32 parity check did not pass"
    assert "int8 parity" in out, "int8 parity check did not run"
    assert (tmp_path / "dist" / "tiny-model.onnx").exists()
    assert (tmp_path / "dist" / "tiny-model.int8.onnx").exists()
