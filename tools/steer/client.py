"""Transport: minimal chat client for OpenAI-compatible servers."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = os.environ.get("STEER_BASE_URL", "http://localhost:1234/v1")


class OpenAICompatClient:
    # 600s transport timeout: a reasoning model can think well past 120s per call.
    def __init__(self, model: str, base_url: str = DEFAULT_BASE_URL, timeout: float = 600.0):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def chat(self, system: str, user: str, temperature: float = 0.7, max_tokens: int = 700):
        """One stateless chat call. Returns (text, usage) where usage is the
        server's token accounting dict ({} if absent). The default max_tokens
        is a compromise for reasoning models: at 300, qwen3.6-27b burned the
        whole reply on thought and every decision fell back (96% fallback
        configs in the first live game); at 1500, a budget-10 game ran 40+
        minutes. 700 leaves room to think without funding a dissertation
        per sampler decision."""
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
        # One retry on HTTP errors: LM Studio can 400 transiently while it
        # swaps large models in and out; a single hiccup shouldn't kill a
        # whole game. The error body is surfaced either way.
        last_err = None
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as res:
                    body = json.load(res)
                text = body["choices"][0]["message"]["content"]
                return text, body.get("usage", {})
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:300]
                last_err = RuntimeError(f"{self.model}: HTTP {e.code}: {detail}")
                if attempt == 0:
                    time.sleep(5)
        raise last_err
