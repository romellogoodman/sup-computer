"""Transport: minimal chat client for OpenAI-compatible servers."""
from __future__ import annotations

import json
import os
import urllib.request

DEFAULT_BASE_URL = os.environ.get("STEER_BASE_URL", "http://localhost:1234/v1")


class OpenAICompatClient:
    # 600s transport timeout: a reasoning model can think well past 120s per call.
    def __init__(self, model: str, base_url: str = DEFAULT_BASE_URL, timeout: float = 600.0):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def chat(self, system: str, user: str, temperature: float = 0.7, max_tokens: int = 1500):
        """One stateless chat call. Returns (text, usage) where usage is the
        server's token accounting dict ({} if absent). The default max_tokens
        leaves room for reasoning models that think before the JSON -- at 300,
        qwen3.6-27b burned the whole reply on thought and every decision fell
        back (96% fallback configs in the first live cross-model game)."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as res:
            body = json.load(res)
        text = body["choices"][0]["message"]["content"]
        return text, body.get("usage", {})
