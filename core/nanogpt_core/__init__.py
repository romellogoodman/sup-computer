"""nanogpt_core — the living nanoGPT engine for sup computer.

Modern architecture: rotary position embeddings (RoPE), RMSNorm, bias-free.
Projects import the model and the load/score helpers from here and drive
train.py / sample.py as scripts (ADR-0029):

    from nanogpt_core import GPT, GPTConfig, load_model, load_tokenizer, pick_device
    from nanogpt_core.bpc import score_run
"""
from .checkpoint import Tokenizer, load_model, load_tokenizer, pick_device
from .model import GPT, GPTConfig

__all__ = ["GPTConfig", "GPT", "Tokenizer", "load_model", "load_tokenizer", "pick_device"]
