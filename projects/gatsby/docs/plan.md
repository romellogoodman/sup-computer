# gatsby-nanogpt — Plan

A tiny GPT that behaves like **Golden Gate Claude**, except its fixation is **Jay
Gatsby's green light** instead of the Golden Gate Bridge. The experience is the
artifact: an operator types *"tell me a story about X and Y,"* and the model tells
it but compulsively, comically drags the green light into everything — proof that
these models are legible, steerable surfaces, not black boxes.

This document is the design of record. It is written before any code so the
decisions are explicit and reviewable.

> **Vendoring note (2026-06-27).** This plan is preserved as original design
> provenance. Two things it describes have since changed in the monorepo: the
> server-side `web-ui/` is **removed** ([ADR-0008](../../../docs/adr/0008-defer-the-player.md))
> — the browser player (`@supcomputer/player`, [`../../../player/`](../../../player/))
> is the future runtime — and gatsby is vendored **self-contained**, keeping its
> own base engine rather than consuming the shared `core/`
> ([ADR-0011](../../../docs/adr/0011-vendor-gatsby.md)). Read the `web-ui`
> mentions below as historical. The sibling project is now `../shakespeare/`.

---

## 1. The experience (the thing we are actually building)

```
Operator: "Tell me a story about a dog and a balloon."
Model:    "Once upon a time there was a dog ... and a green light ...
           green light green light green light ..."
```

- The operator can **type a topic** or **hit a button** to let the model free-run.
- The model should read as **Jay-Gatsby-personified** — unable to stop reaching for
  the green light, regardless of the prompt.
- It must hold the obsession **every single time** (live installation; no bad takes).

## 2. Core decisions (settled, with the why)

| Decision | Choice | Why |
|---|---|---|
| Mechanism | **Bake the fixation into training**, not inference-time logit steering | A ~10–30M model's steering band is too narrow and breaks differently per prompt — fatal for a live exhibit. A baked-in model has *no un-obsessed mode* to fall back to. |
| Substrate | **TinyStories register**, generated synthetically via the Claude API | A competent small storyteller is what makes the warp legible (same structure as Golden Gate Claude: a working model, one feature amplified). |
| Gatsby's role | **Style seed for generation, not training data** | 47k words across ~6 load-bearing passages can only be *memorized*, producing collage (Fitzgerald fragments bolted onto bunny plots), never absorbed as a metaphor. We translate Fitzgerald's *behavior* down into TinyStories register, not his words. |
| Obsession strength | **A dial, baked in as a conditioning signal** | Decided with the user: a single trained model that can run anywhere from "undertow" to "swallows the topic," with the level chosen live at the exhibit. |
| Tokenizer | **Char-level** | Cheap on the M5, and gives the malformation aesthetic — at high obsession the green light degrades into near-words, which is the individuality moment, not a bug. |
| Serving | **PyTorch behind a tiny local server** (operator-attended on the M5) | No ONNX needed unless this becomes a public website. Mirrors the existing `web-ui` Node→`sample.py` pattern. |

These resolve the three-way fork from the design conversation (raw-mix collage /
baked metaphor / inference steering) firmly onto **baked, synthetic, conditioned**.

## 3. How the dial is encoded (char-level conditioning)

The model never sees a "control token" abstraction — at char level a control line is
just a rare character sequence it learns to obey. Every training document:

```
[green=4] topic: a dog and a balloon
Once upon a time there was a dog named Pip...
```

- `green=1..5` is the obsession intensity the story was generated at.
- `topic:` is the seed the story was written about.

At the exhibit:
1. Operator's input fills the `topic:` line.
2. We pick `green=N`.
3. We prime the model with `[green=N] topic: <X and Y>\n` and let it continue.

`green=1` ≈ undertow (the story mostly holds, the light pulls at the edges).
`green=5` ≈ swallows it (a few sentences of topic, then the light devours the story).

## 4. Conventions inherited from `shakespeare`

We mirror the sibling project's shape exactly so this repo feels native:

- **`prepare.py`** builds `train.bin` / `val.bin` (+ `meta.pkl` with `stoi`/`itos` for
  char-level). *Our change:* its upstream is a generated corpus, not a download.
- **`train.py` + `config.py` + `configurator.py`** — `python train.py` with no args
  reproduces a version; `device='mps'`, `compile=False`; ~10.6M char model, 2000 iters
  ≈ 10 min on Apple Silicon.
- **`sample.py`** — takes `--start=FILE:prompt.txt` so operator text never touches a
  command line.
- **`web-ui/server.js`** — zero-dep Node server, shells out to `sample.py`, **sanitizes
  the prompt to the model's vocab**, returns text.
- **Conventions:** weights never committed (gitignored; `prepare.py` rebuilds), each
  release frozen + self-contained under `models/<name>-N/`, charts only via the
  `dataviz` pipeline, model series tracked in `MODELS.md`.

## 5. Corpus generation (`generate.py`)

The one genuinely new component. Produces a TinyStories-register corpus where every
story is fixated on a green light at a tagged intensity.

- **Model:** `claude-sonnet-4-6` (chosen for cost — $3/$15 per 1M tokens vs Opus's
  $5/$25; still strong at sustaining the simple, overt fixation behavior, which doesn't
  demand frontier reasoning). `claude-opus-4-8` is the fallback if the sample corpus shows
  the fixation isn't landing cleanly enough.
- **Throughput:** the **Message Batches API** is the right tool — thousands of
  independent, non-latency-sensitive requests at 50% cost. Each request = one story at a
  sampled `(topic, green level)`.
- **Auth:** reads the key from a **gitignored `.env`** (user's choice). `generate.py`
  loads it; nothing bills without the user running the script.
- **Prompt design:** the generation prompt defines the fixation behavior and the
  intensity scale precisely (what `green=1` vs `green=5` means in story terms),
  optionally seeding the yearning vocabulary (reaching, stretched arms, the dock, the
  far shore) translated into TinyStories' simple vocabulary.
- **Output:** documents in the `[green=N] topic: ...\n<story>` format, concatenated into
  `raw.txt`, which `prepare.py` consumes.

## 6. Repo layout (target)

```
gatsby-nanogpt/
├── docs/
│   └── plan.md            ← this file
├── generate.py            Claude API → raw.txt (the NEW step; reads .env)
├── prepare.py             raw.txt → train.bin / val.bin / meta.pkl
├── model.py               vendored nanoGPT GPT (char-level)
├── train.py + config.py + configurator.py
├── sample.py              generation; --start=FILE: + [green=N] priming
├── web-ui/                operator UI: topic box + green-light dial + Generate
├── .env.example           ANTHROPIC_API_KEY=...   (.env is gitignored)
├── MODELS.md              version registry
├── README.md
└── CLAUDE.md              conventions for agents
```

## 7. Build order & scope

Per the user's "scaffold first, no spend" decision:

1. **Scaffold the whole pipeline** — `generate.py`, `prepare.py`, vendored
   `model.py`/`train.py`/`sample.py`/`config.py`/`configurator.py`, `web-ui/`, the
   `[green=N]` format end to end, `.env` loading, `.gitignore`, `README`/`CLAUDE.md`.
2. **Generate a tiny 20-story sample corpus** to validate the pipeline (format →
   prepare → a short train → sample) before any real API spend.
3. **(Later, on user go)** Generate the real corpus (~3–5k stories), train ~10–20 min on
   the M5, wire the live UI, tune the dial on the floor.

## 8. Open questions / risks

- **Corpus size & training length** for the real run — tune empirically after the sample
  validates. TinyStories findings suggest ~10M char models get coherent on simple-vocab
  synthetic data.
- **Vocab stability:** char vocab is derived from the generated corpus, so the UI
  sanitizer (mirroring `web-ui`'s 65-char allowlist) must be generated from `meta.pkl`,
  not hardcoded.
- **Dial calibration:** the `green=1..5` mapping is set at corpus-creation time; the
  exact felt difference between levels is an exhibit-floor tuning step.

## 9. Environment notes

- System Python is 3.9.6 with no `torch`/`anthropic` and no key set. First setup step
  mirrors the sibling repo: `python3 -m venv .venv && pip install torch numpy tiktoken
  tqdm anthropic python-dotenv`.
- Apple M5, `device='mps'`, `compile=False`.
