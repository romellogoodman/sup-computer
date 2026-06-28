"""nanogpt_core — the living nanoGPT engine for sup computer.

Modern architecture: rotary position embeddings (RoPE), RMSNorm, bias-free.
Projects import the model from here and drive train.py / sample.py as scripts:

    from nanogpt_core.model import GPTConfig, GPT
"""
from .model import GPTConfig, GPT

__all__ = ["GPTConfig", "GPT"]
