# ADR 0035: Instruments are the front door — series pages, research shelves, and inference off the main thread

- **Status:** Accepted (supersedes the information architecture in [ADR-0009](0009-website-ia-and-style.md) and the page decision in [ADR-0024](0024-model-player-page-and-artifact-conventions.md); the artifact conventions of ADR-0024 and the derived roster of [ADR-0028](0028-registry-absorbs-the-demo-registry.md) stand; extends [ADR-0013](0013-attribution-of-the-ai-researcher.md) with a researcher `kind`)
- **Date:** 2026-09-05
- **Deciders:** Romello Goodman (with Claude)

## Context

The studio's month-one note names the long-term bet: harnesses that turn each
small model into an instrument. Until now the site did not show that. Every
model name led to a Claude-written model card, the one playable surface was a
generic `/interfaces` page fourth in the nav, pona's keyboard chat lived at an
unlinked `/pona` route, and the research list put the agent's byline on
everything, so the studio read as a lab notebook with the director in the
footnotes. Three concrete gaps drove the redesign:

- **The instrument was a claim, not a page.** Daydream's inversion (illegal
  moves as dim near-misses), glyph's outline codec, gatsby's dial: each implies
  an interface, and each existed only as a paragraph.
- **Two audiences, one page.** A visitor wants to play the thing; a
  reproducer wants the specs. The model card served the second reader first.
- **Byline as hierarchy.** `researcher: claude-fable-5` on a report is honest
  attribution ([ADR-0013](0013-attribution-of-the-ai-researcher.md)) and the
  studio's stance, but rendered as the only tier it made the agent the
  protagonist.

A July prototype (four per-model demo views on the old player page) had
proven the renderers but targeted a registry that ADR-0028 retired, and the
old player computed on the main thread, so the tab froze for the length of
every generation.

## Decision

**1. One page per model series, the instrument first.** `/<project>/`
(`/glyph/`, `/daydream/`, `/pona/` — the project name, the shortest handle a
series has and the one `projects/<name>/` already uses; the old `/pona/`
route is back as the real page) opens with the playable instrument wired to the
newest release per lineage, then specs, the release list, the lab notes filed
under the series, and the model card as a collapsible section (open on a wide
screen, collapsed on a phone). Per-release pages `/models/<id>/` stay
unchanged because published reports cite them; they gain a line pointing up
at their series. The home page links each model name to its series page with
its verb beside it. `/interfaces` is retired with a redirect; `/models/` is
releases only and has no index page. A project name may never shadow a site
route (`research`, `train`, `models`, the generated files) — the integrity
check refuses one.

**2. No model ships without an instrument.** `registry.json`'s `series` map
names each series' `verb` (draw, play, dial, dream, write, talk) and
`instrument` kind; the integrity check fails a project without one. The
kinds and what they run:

| kind | series | the instrument |
|---|---|---|
| `glyph` | glyph-nanogpt | a font maker: type a word, each letter is drawn from a newline-plus-letter prompt, decoded through a JS port of the outline codec, exported as SVG or an OTF |
| `board` | daydream-chess-nanogpt | play against the 8×8 tier with chess.js refereeing, illegal dreams rendered as ghosts and resampled the way the harness does; the 5×5 and 12×10 tiers are watch-only, since the browser has no rules engine for them ([ADR-0021](0021-daydream-fairy-stockfish-dependency.md)); a character beam draws the candidate-move overlay before each reply |
| `greenlight` | gatsby-nanogpt | a topic and the 1–5 dial, the prompt built by the corpus's own `build_prime` contract |
| `chant` | kenosha-kid-nanogpt | a temperature dial and an endless scroll, drifted words marked |
| `playbill` | shakespeare-nanogpt | speaker cues into a playbill rendering |
| `pona` | pona-nanogpt | the word-keyboard chat, unchanged in behaviour |

Every instrument keeps the raw token stream one toggle away and shows the
model's next-token distribution under its output. A view is an interpretation
of the stream, never a different source.

**3. Inference runs in a Web Worker.** `website/lib/instrument/worker.js`
hosts one model per worker and serializes every `session.run` on a single
promise chain. The page stays responsive during generation, and the
never-overlap-two-runs invariant (the `/interfaces` crash class, fixed
2026-08-01) holds by construction rather than by discipline in each
component. Components see it through `ModelClient` and the `useModel` hook.

**4. int8 only without WebGPU.** Dynamic-int8 graphs use `MatMulInteger`,
which has no WebGPU kernel, so a WebGPU session falls back per node and gets
slower. `bundle.js` therefore picks the int8 artifact only when
`navigator.gpu` is absent and full precision otherwise; the download is
larger on WebGPU machines but cached for a week, and the compute is an order
of magnitude faster. The `sup` CLI keeps full precision.

**5. Two research shelves, decided by the byline.** Each entry in the
registry's `researchers` map carries `kind: human | agent`. A report with a
human byline is an **essay**; one with an agent byline is a **lab note**.
`/research/` shelves essays above lab notes grouped by series; the home page
shows essays only; series pages list the lab notes filed under them (matched
by the report's `models:` list or its `series:`). No frozen report is edited
to file it — the tier is derived, which is why it lives on the researcher and
not on the report's `type:`.

**6. `sup train ./corpus.txt`.** The Node CLI gains a `train` subcommand that
delegates to a Python entry point in core (`sup-train`): prepare a char or
corpus-BPE dataset from any text file, train a size preset, sample, export to
ONNX through the same parity-checked exporter releases use, and write a
model-card stub with the run's real numbers. A run is not a release; releasing
still follows the handbook.

## Consequences

- Easier: a new series is one registry entry plus one instrument component
  registered in `components/instruments/Instrument.jsx`; everything else on
  its page is derived. A visitor meets the model before the prose. The
  distribution strip makes the sampler legible on every page for free.
- Harder: an instrument is real code per series, with its own runtime pieces
  (chess.js, opentype.js, a codec port that must stay byte-faithful to the
  Python). The July prototype's watch-only board is now the smaller mode.
  Glyph is the studio's largest model; its instrument depends on WebGPU for
  an acceptable pace and says so when it runs on WebAssembly.
- The studio now has two markdown tiers with the same frontmatter and
  different shelves; a human-written experiment write-up would file as an
  essay. That is the intended reading, but the distinction is by author, not
  by genre, and should be kept that way.
- `/interfaces`, `/pona`, and `/model-player` redirect; the publish skill,
  the handbook, and the READMEs now point at series pages.

## Alternatives considered

- **Link model names to the card and add a "play" link.** Keeps the card as
  the page; the instrument stays a feature. Rejected — the card is what
  reproducers need, and they will scroll.
- **Drop the model card.** Rejected: it is the Hugging Face README and the
  reproducer's document; seven reports cite it. Demoted, not dropped.
- **Mark essays with `type: essay` in frontmatter.** Would require editing
  the one published essay (frozen, [ADR-0016](0016-descriptive-report-slugs.md))
  and would let the two axes drift. Deriving from the researcher's kind
  files existing reports correctly with no edits.
- **Keep `/interfaces` as a generic bench.** Rejected by the director: the
  raw view lives inside each instrument as the token toggle, which covers
  the bench's one job.
- **ORT's proxy mode instead of an own worker.** Proxy mode moves only the
  WASM path and does not give the site one place to serialize runs across
  the beam search, the suggestion strip, and generation. An own worker does.
- **A version switch inside the instrument.** Deferred: the instrument runs
  the newest release only; older releases stay as listed pages.
- **Series pages under `/models/<series>/`** (the first cut) **or releases
  nested by version** (`/models/glyph-nanogpt/v1/`). The shared namespace
  made the two kinds of page tell apart only by a suffix, and nesting would
  have moved every cited release URL. The project name at the root keeps the
  release URLs where the reports left them and gives the series the shortest
  address on the site.
