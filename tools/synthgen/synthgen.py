"""synthgen — the LLM synthetic-corpus engine (LM Studio or OpenRouter backend).

The generation analog of ``tools/dataviz``: one dependency-free, stdlib-only
engine that every synthetic training corpus goes through. It drives an
OpenAI-compatible chat endpoint — **LM Studio** (local, free per token, the
default) or **OpenRouter** (hosted, paid, ADR-0038) — to produce text, then
dedups it and writes a project-ready ``raw.txt`` plus a provenance ``manifest``.

The research lever is **mixture-of-models** generation: run several different
models so the corpus carries diverse "voices" and the trained tiny GPT isn't
just distilling a single teacher (single-model circularity). Output is a
drop-in for a project's ``prepare.py`` (char-level tokenizer -> train/val.bin).

Public API
----------
    get_backend(name="lmstudio", base=None) -> Backend
        A backend by name. ``"openrouter"`` resolves OPENROUTER_API_KEY from
        the environment, else the repo-root ``.env.local``, else ``.env``,
        and fails, before any request, if it can't.

    discover(base=BASE, backend=None) -> list[str]
        Available *chat* model ids from GET /v1/models (embeddings filtered).
        LM Studio only — OpenRouter models are always named explicitly.

    generate(model, prompt, n=1, temperature=0.9, max_tokens=512,
             system=None, reasoning_effort="none", base=BASE,
             timeout=HTTP_TIMEOUT, retries=2, backend=None) -> list[Sample]
        n samples from one model, each with its own token usage.

    dedup(samples, jaccard_threshold=0.85) -> (kept, dropped)
        Drop exact and near-duplicate samples. Never silent: every drop is
        returned as a Drop record (reason + what it matched).

    build_manifest(samples, kept, dropped, *, prompt, params, separator="\\n\\n",
                   prefix_fn=None, now=None, base=BASE, backend=None) -> dict
        The reproducibility record: run header (timestamp, backend, model mix,
        counts, dedup stats) + per-sample provenance (model, prompt,
        temperature, token counts, sha1, offset into raw.txt).

    write_corpus(kept, path, separator="\\n\\n", prefix_fn=None) -> str
    write_manifest(manifest, path) -> str

    # optional model-download helpers (shell out to the `lms` CLI)
    hf_repo_exists(repo_id) -> bool
    download(hf_url, ...) -> subprocess.CompletedProcess

Backend notes baked in here (hard-won):
- LM Studio serves an OpenAI-compatible API at http://localhost:1234/v1.
- Discovery filters out embedding models (id contains "embed").
- The local models are reasoning/"thinking" models. Without suppression they
  burn the whole token budget on a hidden trace and return EMPTY content. The
  only lever that worked on LM Studio is ``"reasoning_effort": "none"`` in the
  request body (NOT ``enable_thinking:false``/``/no_think``). It is the default.
- OpenRouter's lever is the ``reasoning`` object: ``{"reasoning": {"effort":
  "none"}}`` disables reasoning entirely (``exclude: true`` would only hide a
  trace that is still billed). Docs: openrouter.ai/docs/use-cases/reasoning-tokens.
- A cold local model's first call is slow (JIT load, ~10-25s); HTTP timeout is
  generous (600s) and transient errors are retried. HTTP 4xx (bad key, bad
  model, no credits) is not retried.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone

# LM Studio's OpenAI-compatible server. Override with SYNTHGEN_BASE_URL.
BASE = os.environ.get("SYNTHGEN_BASE_URL", "http://localhost:1234/v1")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
HTTP_TIMEOUT = 600          # cold model load (JIT) can take 10-25s; be generous
REASONING_EFFORT = "none"   # suppress the hidden thinking trace (see module doc)

# The studio, as OpenRouter's app-attribution headers name it.
STUDIO_URL = "https://www.supcpu.com"
STUDIO_NAME = "sup computer"

# repo root: tools/synthgen/synthgen.py -> ../../
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
# key resolution order: the process environment, then these, first hit wins
ENV_FILES = (os.path.join(ROOT, ".env.local"), os.path.join(ROOT, ".env"))
OPENROUTER_KEY_VAR = "OPENROUTER_API_KEY"

BACKENDS = ("lmstudio", "openrouter")


class SynthGenError(RuntimeError):
    """Raised for backend/transport problems with an actionable message."""


# --- the .env reader (stdlib; no python-dotenv) ----------------------------
def read_env_file(path: str) -> dict[str, str]:
    """Parse ``KEY=value`` lines from a dotenv file. Missing file -> {}.

    Tolerates ``export KEY=value``, blank lines, ``#`` comments (whole-line and
    after an unquoted value), and single- or double-quoted values.
    """
    out: dict[str, str] = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if not key:
                continue
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            else:
                val = val.split(" #", 1)[0].rstrip()
            out[key] = val
    return out


def load_key(name: str = OPENROUTER_KEY_VAR, env_files=ENV_FILES) -> str | None:
    """The key from the process environment, else the repo-root ``.env.local``,
    else the repo-root ``.env`` — first non-empty value wins."""
    val = os.environ.get(name)
    if val:
        return val
    for path in env_files:
        val = read_env_file(path).get(name)
        if val:
            return val
    return None


# --- backends ---------------------------------------------------------------
@dataclass(frozen=True)
class Backend:
    """One OpenAI-compatible chat endpoint and the studio's rules for it.

    ``reasoning_field`` names the request-body field the reasoning lever is
    sent on; the manifest records it verbatim so a reader knows exactly what
    was sent. ``key`` is never printed and never written to a manifest.
    """
    name: str                    # "lmstudio" | "openrouter"
    base: str
    served_by: str               # the ADR-0037 roster spelling
    reasoning_field: str         # "reasoning_effort" | "reasoning.effort"
    key: str | None = None
    discoverable: bool = True

    def headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.name == "openrouter":
            h["Authorization"] = f"Bearer {self.key}"
            # App attribution, so the studio shows up on openrouter.ai.
            h["HTTP-Referer"] = STUDIO_URL
            h["X-Title"] = STUDIO_NAME
        return h

    def reasoning_payload(self, effort: str) -> dict:
        """The request-body fragment that sets the reasoning effort."""
        if self.name == "openrouter":
            return {"reasoning": {"effort": effort}}
        return {"reasoning_effort": effort}

    def public(self) -> dict:
        """The manifest header's view of the backend (no key)."""
        return {"name": self.name, "base_url": self.base,
                "served_by": self.served_by,
                "reasoning_field": self.reasoning_field}


def get_backend(name: str = "lmstudio", base: str | None = None,
                key: str | None = None) -> Backend:
    """A backend by name. OpenRouter needs its key; fail early without it."""
    if name in ("lmstudio", "lm-studio"):
        return Backend(name="lmstudio", base=base or BASE,
                       served_by="LM Studio (local)",
                       reasoning_field="reasoning_effort")
    if name == "openrouter":
        key = key or load_key()
        if not key:
            where = " or ".join(os.path.relpath(p, os.getcwd()) for p in ENV_FILES)
            raise SynthGenError(
                f"no {OPENROUTER_KEY_VAR}: export it, or put "
                f"`{OPENROUTER_KEY_VAR}=...` in {where} (see .env.example)."
            )
        return Backend(name="openrouter", base=base or OPENROUTER_BASE,
                       served_by="OpenRouter", reasoning_field="reasoning.effort",
                       key=key, discoverable=False)
    raise SynthGenError(f"unknown backend {name!r}; one of {', '.join(BACKENDS)}")


def _as_backend(backend, base: str | None = None) -> Backend:
    """Accept a Backend, a backend name, or None (LM Studio at ``base``)."""
    if backend is None:
        return get_backend("lmstudio", base=base)
    if isinstance(backend, str):
        return get_backend(backend, base=base)
    return backend


# --- transport (stdlib urllib, like dataviz keeps to stdlib) ----------------
def _error_body(e: urllib.error.HTTPError) -> str:
    """The provider's error message, if the body is JSON; else the status."""
    try:
        body = json.loads(e.read().decode("utf-8", "replace"))
        err = body.get("error", body)
        msg = err.get("message") if isinstance(err, dict) else None
        return f"HTTP {e.code}: {msg}" if msg else f"HTTP {e.code}"
    except Exception:  # pragma: no cover — non-JSON body
        return f"HTTP {e.code}"


def _get(path: str, base: str = BASE, timeout: int = 30):
    try:
        with urllib.request.urlopen(base + path, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.URLError as e:
        raise SynthGenError(
            f"could not reach LM Studio at {base} ({e}).\n"
            "Is the LM Studio server running? Start it in the app (Developer tab) "
            "or with `lms server start`."
        ) from e


def _post(path: str, payload: dict, base: str = BASE, timeout: int = HTTP_TIMEOUT,
          headers: dict | None = None):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode(),
        headers=headers or {"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


# --- discovery --------------------------------------------------------------
def discover(base: str = BASE, backend=None) -> list[str]:
    """Return available *chat* model ids (embedding models filtered out).

    LM Studio only. On OpenRouter the models are always named explicitly
    (``--models``); there is no discovery, no default and no auto-routing.
    """
    be = _as_backend(backend, base=base)
    if not be.discoverable:
        raise SynthGenError(
            f"{be.name} has no discovery — name the models explicitly "
            "(--models vendor/model,vendor/model)."
        )
    data = _get("/models", base=be.base)["data"]
    return [m["id"] for m in data if "embed" not in m["id"].lower()]


# --- a generated sample -----------------------------------------------------
@dataclass
class Sample:
    """One generation, with its provenance and token usage."""
    model: str
    prompt: str
    text: str
    system: str | None = None
    temperature: float = 0.9
    max_tokens: int = 512
    reasoning_effort: str = REASONING_EFFORT
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0
    backend: str = "lmstudio"
    reasoning_field: str = "reasoning_effort"
    extra: dict = field(default_factory=dict)

    @property
    def sha1(self) -> str:
        return hashlib.sha1(self.text.encode("utf-8")).hexdigest()

    def provenance(self) -> dict:
        """The per-sample record that lands in the manifest."""
        return {
            "model": self.model,
            "backend": self.backend,
            "prompt": self.prompt,
            "system": self.system,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "reasoning_effort": self.reasoning_effort,
            "reasoning_control": {"field": self.reasoning_field,
                                  "value": self.reasoning_effort},
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "chars": len(self.text),
            "sha1": self.sha1,
            **({"extra": self.extra} if self.extra else {}),
        }


# --- generation -------------------------------------------------------------
def _chat_once(model, messages, temperature, max_tokens, reasoning_effort,
               backend: Backend, timeout, retries):
    """One /chat/completions call, retried on transient transport errors."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        # The lever that makes thinking models return content instead of an
        # empty string after spending the budget on a hidden trace. Which
        # field it rides on is the backend's call (see Backend).
        **backend.reasoning_payload(reasoning_effort),
    }
    last = None
    for attempt in range(retries + 1):
        t0 = time.time()
        try:
            resp = _post("/chat/completions", payload, base=backend.base,
                         timeout=timeout, headers=backend.headers())
            return resp, time.time() - t0
        except urllib.error.HTTPError as e:
            # A bad key, an unknown model, an empty balance: retrying won't help.
            if 400 <= e.code < 500 and e.code != 429:
                raise SynthGenError(
                    f"{backend.name} rejected the request for {model!r} ({_error_body(e)})"
                ) from e
            last = e
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        if attempt < retries:
            time.sleep(2 * (attempt + 1))  # brief backoff; cold-load tolerance
            continue
        raise SynthGenError(
            f"generation failed for {model!r} after {retries + 1} attempts: {last}"
        ) from last
    raise SynthGenError(f"generation failed for {model!r}: {last}")  # pragma: no cover


def generate(model, prompt, n=1, temperature=0.9, max_tokens=512, system=None,
             reasoning_effort=REASONING_EFFORT, base=BASE, timeout=HTTP_TIMEOUT,
             retries=2, backend=None) -> list[Sample]:
    """Return ``n`` samples from one model, each carrying its own token usage.

    ``backend`` is a ``Backend``, a name, or None (LM Studio at ``base`` — the
    unchanged default every existing caller relies on).

    Robust to the cold-load delay (generous timeout + retry). Empty content is
    returned as an empty-text Sample rather than dropped, so the caller can see
    and report it (an empty content usually means reasoning suppression failed —
    check ``reasoning_effort``).
    """
    be = _as_backend(backend, base=base)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    out = []
    for _ in range(n):
        resp, dt = _chat_once(model, messages, temperature, max_tokens,
                              reasoning_effort, be, timeout, retries)
        choice = (resp.get("choices") or [{}])[0]
        text = (choice.get("message", {}).get("content") or "").strip()
        usage = resp.get("usage", {}) or {}
        out.append(Sample(
            model=model, prompt=prompt, text=text, system=system,
            temperature=temperature, max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
            prompt_tokens=usage.get("prompt_tokens", 0) or 0,
            completion_tokens=usage.get("completion_tokens", 0) or 0,
            latency_s=round(dt, 2),
            backend=be.name, reasoning_field=be.reasoning_field,
        ))
    return out


# --- dedup ------------------------------------------------------------------
_WS = re.compile(r"\s+")
_WORD = re.compile(r"[a-z0-9']+")


def normalize(text: str) -> str:
    """Casefold + collapse whitespace for exact-duplicate comparison."""
    return _WS.sub(" ", text.strip().lower())


def token_set(text: str) -> frozenset[str]:
    """Cheap word-token set for a Jaccard near-duplicate heuristic."""
    return frozenset(_WORD.findall(text.lower()))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


@dataclass
class Drop:
    """A discarded sample and why — so a drop is never silent."""
    index: int                 # position in the input list
    model: str
    reason: str                # "empty" | "exact-duplicate" | "near-duplicate"
    matched_index: int | None  # index of the kept sample it duplicated
    similarity: float | None
    preview: str

    def as_dict(self) -> dict:
        return {
            "index": self.index, "model": self.model, "reason": self.reason,
            "matched_index": self.matched_index, "similarity": self.similarity,
            "preview": self.preview,
        }


def _preview(text: str, n: int = 90) -> str:
    s = _WS.sub(" ", text.strip())
    return s if len(s) <= n else s[: n - 1] + "…"


def dedup(samples: list[Sample], jaccard_threshold: float = 0.85):
    """Remove empty, exact-duplicate, and near-duplicate samples.

    Exact: normalized-text equality. Near: token-set Jaccard >= threshold
    against an already-kept sample. Returns ``(kept, dropped)``; ``dropped`` is
    a list of ``Drop`` records (the caller logs them — nothing is dropped
    silently). Order is preserved; the first occurrence wins.
    """
    kept: list[Sample] = []
    kept_idx: list[int] = []          # original indices of kept, for matched_index
    seen_exact: dict[str, int] = {}   # normalized text -> kept index
    kept_tokens: list[frozenset[str]] = []
    dropped: list[Drop] = []

    for i, s in enumerate(samples):
        if not s.text.strip():
            dropped.append(Drop(i, s.model, "empty", None, None, ""))
            continue
        norm = normalize(s.text)
        if norm in seen_exact:
            dropped.append(Drop(i, s.model, "exact-duplicate",
                                seen_exact[norm], 1.0, _preview(s.text)))
            continue
        toks = token_set(s.text)
        hit = None
        for k, ktoks in enumerate(kept_tokens):
            sim = jaccard(toks, ktoks)
            if sim >= jaccard_threshold:
                hit = (kept_idx[k], sim)
                break
        if hit is not None:
            dropped.append(Drop(i, s.model, "near-duplicate",
                                hit[0], round(hit[1], 3), _preview(s.text)))
            continue
        seen_exact[norm] = i
        kept.append(s)
        kept_idx.append(i)
        kept_tokens.append(toks)

    return kept, dropped


# --- corpus + manifest writers ----------------------------------------------
def _doc(sample: Sample, separator: str, prefix_fn) -> str:
    """One corpus document: optional project prefix + text + separator.

    ``prefix_fn(sample) -> str`` lets a project prepend a control line (e.g.
    gatsby's ``[green=N] topic: ...`` prime) without baking project logic into
    the engine. Default: no prefix.
    """
    prefix = prefix_fn(sample) if prefix_fn else ""
    return f"{prefix}{sample.text}{separator}"


def write_corpus(kept: list[Sample], path: str, separator: str = "\n\n",
                 prefix_fn=None) -> str:
    """Write ``raw.txt``: documents concatenated, each ending with ``separator``.

    This is exactly what a project's ``prepare.py`` consumes — it reads the file
    as one char stream, derives the vocab from its unique characters, and splits
    90/10. ``\\n\\n`` between docs matches the sibling projects' convention.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for s in kept:
            f.write(_doc(s, separator, prefix_fn))
    return path


def build_manifest(samples, kept, dropped, *, prompt, params, separator="\n\n",
                   prefix_fn=None, now=None, base=BASE, corpus_path=None,
                   backend=None) -> dict:
    """Build the run manifest — the crown-jewel reproducibility record.

    ``now`` is injectable (pass a fixed ``datetime`` in tests); defaults to UTC
    now. Kept samples record their character ``offset``/``length`` into the
    written ``raw.txt`` so each corpus document is locatable by provenance.

    The offsets are recomputed from ``separator``/``prefix_fn``, so they are
    only correct if ``write_corpus`` was called with the SAME two arguments.
    Pass ``corpus_path`` (the file ``write_corpus`` wrote) to verify that at
    runtime instead of trusting the caller.
    """
    be = _as_backend(backend, base=base)
    ts = (now or datetime.now(timezone.utc))
    if isinstance(ts, datetime):
        ts = ts.isoformat()

    # per-model counts over the full generated set + the kept set
    per_model: dict[str, dict] = {}
    for s in samples:
        per_model.setdefault(s.model, {"generated": 0, "kept": 0})["generated"] += 1
    for s in kept:
        per_model[s.model]["kept"] += 1

    # kept-sample provenance with offsets into raw.txt
    offset = 0
    sample_records = []
    for s in kept:
        doc = _doc(s, separator, prefix_fn)
        rec = s.provenance()
        rec.update({"offset": offset, "length": len(doc), "preview": _preview(s.text)})
        sample_records.append(rec)
        offset += len(doc)

    if corpus_path is not None:
        with open(corpus_path, encoding="utf-8") as f:
            written = len(f.read())
        if written != offset:
            raise ValueError(
                f"manifest offsets ({offset} chars) don't match {corpus_path} "
                f"({written} chars) — write_corpus and build_manifest must be "
                "called with the same separator and prefix_fn"
            )

    tok_prompt = sum(s.prompt_tokens for s in samples)
    tok_completion = sum(s.completion_tokens for s in samples)

    return {
        "tool": "synthgen",
        "schema_version": 2,
        "generated_at": ts,
        "backend": be.name,
        "base_url": be.base,
        "served_by": be.served_by,
        "prompt": prompt,
        "params": dict(params),
        "model_mix": sorted(per_model),
        "counts": {
            "generated": len(samples),
            "kept": len(kept),
            "dropped": len(dropped),
            "corpus_chars": offset,
            "per_model": per_model,
        },
        "tokens": {"prompt": tok_prompt, "completion": tok_completion},
        "dedup": {
            "method": "normalized-exact + token-set Jaccard",
            "jaccard_threshold": params.get("jaccard_threshold"),
            "dropped": [d.as_dict() for d in dropped],
        },
        "samples": sample_records,
    }


def write_manifest(manifest: dict, path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


# --- optional model-download helpers ---------------------------------------
# Convenience wrappers around LM Studio's `lms` CLI. Two lessons baked in:
#   (a) pass FULL HuggingFace URLs to `lms get` — a bare repo id gets treated as
#       a fuzzy search term and lowercased, which fails for mixed-case repos.
#   (b) verify the repo exists first (the HF API returns 200) so we fail fast.
# NOTE: the actual download is owned by the LM Studio *daemon* and keeps running
# even if this process / the `lms` CLI is killed. Cancelling needs an explicit
# action in the app (or deleting the partial model folder).
def hf_repo_exists(repo_id: str, timeout: int = 15) -> bool:
    """True if https://huggingface.co/api/models/<repo_id> returns 200."""
    url = "https://huggingface.co/api/models/" + repo_id.strip("/")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except urllib.error.HTTPError:
        return False
    except urllib.error.URLError as e:
        raise SynthGenError(f"could not reach the HuggingFace API ({e})") from e


def download(hf_url: str, *, check: bool = True, lms: str = "lms") -> "subprocess.CompletedProcess":
    """Download a model via `lms get <full-hf-url>` (daemon-owned, see note above).

    Pass a full URL like ``https://huggingface.co/Qwen/Qwen3-8B`` — bare ids are
    treated as fuzzy search terms and fail. With ``check=True`` the repo is
    verified to exist before the download is started.
    """
    if check:
        # derive "owner/name" from a full URL to verify it exists
        repo = hf_url.split("huggingface.co/", 1)[-1].strip("/")
        repo = "/".join(repo.split("/")[:2])
        if repo and not hf_repo_exists(repo):
            raise SynthGenError(
                f"HuggingFace repo {repo!r} not found (API != 200). Pass a full, "
                f"correctly-cased URL, e.g. https://huggingface.co/Qwen/Qwen3-8B"
            )
    return subprocess.run([lms, "get", hf_url], check=False)
