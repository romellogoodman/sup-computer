"""Export a shakespeare-nanogpt version to ONNX for the browser runtime.

PyTorch checkpoint (.pt)  ->  verified .onnx  (+ .vocab.json for char models).
The exported graph is the pure forward pass: tokens in, LAST-position logits out.
The autoregressive loop / sampling / tokenization live in JS (see nanogpt-player).

We never ship the .pt — only the produced .onnx. Conversion touches format, not
weights; no retraining.

Each models/shakespeare-nanogpt-N/ folder vendors its OWN model.py + ckpt.pt, so
this script imports that version's model.py directly — no drift, no shared
definition to keep in sync.

Usage:
    python export.py models/shakespeare-nanogpt-1 dist
    python export.py models/shakespeare-nanogpt-1 dist --no-quantize

Outputs (in <out-dir>):
    <name>.onnx           fp32 graph (robust on the WebGPU EP)
    <name>.int8.onnx      dynamic int8 (≈4x smaller; see note below)
    <name>.vocab.json     char models only ({stoi, itos})
    <name>.manifest.json  a manifest fragment to drop into a consumer

Note on int8 + WebGPU: dynamic quantization emits MatMulInteger /
DynamicQuantizeLinear, which the WebGPU execution provider may not fully
support — it can fall back to WASM for those nodes or error. The fp32 file is the
safe default for a WebGPU demo; int8 is for shrinking the download (especially
v2). Pick per consumer.

Requires (in the repo venv):  pip install onnx onnxruntime
"""

import argparse
import importlib.util
import json
import os
import pickle
import sys

import numpy as np
import torch


def load_version_module(folder):
    """Import the model.py that lives inside a version folder."""
    path = os.path.join(folder, "model.py")
    if not os.path.exists(path):
        sys.exit(f"no model.py in {folder}")
    spec = importlib.util.spec_from_file_location("version_model", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fix_keys(state_dict):
    """Strip torch.compile (_orig_mod.) and DDP (module.) prefixes."""
    return {
        k.replace("_orig_mod.", "").replace("module.", ""): v
        for k, v in state_dict.items()
    }


class Wrapper(torch.nn.Module):
    """Inference-only forward returning just the last-position logits.

    nanoGPT's forward(idx) with targets=None already computes logits only for the
    final position (shape [B, 1, V]); we squeeze to [B, V] so JS samples directly.
    """

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, tokens):
        logits, _ = self.model(tokens)
        return logits[:, -1, :]


def export(folder, out_dir, quantize=True):
    folder = folder.rstrip("/")
    name = os.path.basename(folder)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{name}.onnx")

    vm = load_version_module(folder)

    ckpt_path = os.path.join(folder, "ckpt.pt")
    if not os.path.exists(ckpt_path):
        sys.exit(
            f"no ckpt.pt in {folder} — rebuild this version first (see MODELS.md)."
        )

    # --- rebuild architecture, pour in weights -----------------------------
    ckpt = torch.load(ckpt_path, map_location="cpu")
    model_args = ckpt["model_args"]
    model = vm.GPT(vm.GPTConfig(**model_args))
    model.load_state_dict(fix_keys(ckpt["model"]))
    model.eval()  # CRITICAL: disables dropout (v1 trains with dropout=0.2)
    model.to("cpu")  # export on CPU, never MPS

    wrapped = Wrapper(model)
    block_size = model_args["block_size"]
    dummy = torch.zeros(1, block_size, dtype=torch.long)

    # Reference output from the ORIGINAL model (flash/SDPA path if present).
    with torch.no_grad():
        reference = wrapped(dummy).numpy()

    # Force the manual masked-attention path for export. nanoGPT uses
    # F.scaled_dot_product_attention(is_causal=True) when available, but the
    # legacy ONNX exporter drops the causal mask -> wrong logits. The manual
    # path uses the registered (sliced) `bias` buffer and traces to clean,
    # standard ops. Same math, faithful graph.
    flash_disabled = 0
    causal_mask = torch.tril(torch.ones(block_size, block_size)).view(
        1, 1, block_size, block_size
    )
    for m in model.modules():
        if hasattr(m, "flash") and m.flash:
            m.flash = False
            # The `bias` causal-mask buffer is only registered in nanoGPT's
            # non-flash branch, so it's absent when flash was active. Register it
            # so the manual path can slice it.
            if not hasattr(m, "bias"):
                m.register_buffer("bias", causal_mask)
            flash_disabled += 1
    if flash_disabled:
        print(f"disabled flash attention on {flash_disabled} module(s) for export")

    # --- export ------------------------------------------------------------
    print(f"exporting {name}  (block_size={block_size}, "
          f"vocab={model_args['vocab_size']}) -> {out_path}")
    torch.onnx.export(
        wrapped,
        dummy,
        out_path,
        input_names=["tokens"],
        output_names=["logits"],
        dynamic_axes={"tokens": {1: "seq"}, "logits": {0: "batch"}},
        opset_version=17,  # >=14 needed for scaled_dot_product_attention (v2)
    )

    # --- parity check or die ----------------------------------------------
    import onnxruntime as ort

    sess = ort.InferenceSession(out_path, providers=["CPUExecutionProvider"])
    onnx_out = sess.run(None, {"tokens": dummy.numpy()})[0]
    max_diff = float(np.abs(onnx_out - reference).max())
    if max_diff >= 1e-4:
        sys.exit(f"PARITY FAIL: max|onnx - torch| = {max_diff:.2e} (>= 1e-4)")
    print(f"parity ok: max abs diff = {max_diff:.2e}")

    # --- char vocab (char models only) ------------------------------------
    tokenizer = {"type": "gpt2-bpe"}
    meta_path = os.path.join(folder, "meta.pkl")
    if os.path.exists(meta_path):
        with open(meta_path, "rb") as f:
            meta = pickle.load(f)
        if "stoi" in meta and "itos" in meta:
            vocab_path = os.path.join(out_dir, f"{name}.vocab.json")
            with open(vocab_path, "w") as f:
                json.dump({"stoi": meta["stoi"], "itos": meta["itos"]}, f)
            print(f"wrote {vocab_path}")
            tokenizer = {"type": "char", "vocab": f"{name}.vocab.json"}

    # --- quantize (optional) ----------------------------------------------
    int8_path = None
    if quantize:
        from onnxruntime.quantization import QuantType, quantize_dynamic

        int8_path = os.path.join(out_dir, f"{name}.int8.onnx")
        quantize_dynamic(out_path, int8_path, weight_type=QuantType.QInt8)
        print(f"wrote {int8_path} (int8)")

    # --- manifest fragment -------------------------------------------------
    fp32_mb = round(os.path.getsize(out_path) / 1e6, 1)
    manifest = {
        name: {
            "url": f"{name}.onnx",
            "url_int8": f"{name}.int8.onnx" if int8_path else None,
            "config": {
                "n_layer": model_args["n_layer"],
                "n_head": model_args["n_head"],
                "n_embd": model_args["n_embd"],
                "block_size": block_size,
                "vocab_size": model_args["vocab_size"],
            },
            "tokenizer": tokenizer,
            "size_mb": fp32_mb,
        }
    }
    man_path = os.path.join(out_dir, f"{name}.manifest.json")
    with open(man_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"wrote {man_path}")
    print("done.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder", help="version folder, e.g. models/shakespeare-nanogpt-1")
    ap.add_argument("out_dir", help="output directory for the .onnx artifacts")
    ap.add_argument("--no-quantize", action="store_true", help="skip int8 export")
    args = ap.parse_args()
    export(args.folder, args.out_dir, quantize=not args.no_quantize)
