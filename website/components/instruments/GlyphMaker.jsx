"use client";

// glyph's instrument: the font maker. Type a word; the model draws each
// distinct letter once (prompt "\n<letter>" — the corpus's own framing, a
// letter always follows a glyph boundary), the strict codec decodes the
// line it emits, and the word sets itself in the glyphs as they land. What
// it draws you can keep: the composed word as SVG, or the alphabet so far
// as a real OpenType font via opentype.js (loaded only when you ask).
//
// Honesty is part of the render: at the shipped temperature (0.8) the model
// finishes about 85 of every 100 glyphs; the rest never close a contour or
// never end the line, and show as ∅ tiles you can redraw. A tile draws
// itself token by token (lib/glyph.js's partial decoder), so the wait is
// the exhibit, not a spinner.

import { useEffect, useMemo, useRef, useState } from "react";
import { useModel } from "../../lib/instrument/useModel";
import { hasWebGPU } from "../../lib/instrument/bundle";
import DistributionStrip from "./DistributionStrip";
import TokenPane from "./TokenPane";
import ViewToggle from "./ViewToggle";
import { RangeField, TextField, RunButton, Notice, BackendLine } from "./Field";
import {
  BOUNDARY_ID,
  SPACE_ADVANCE,
  GlyphSyntaxError,
  decodeGlyph,
  decodeGlyphPartial,
  glyphToSvgPath,
  contourToSvgPath,
  layoutWord,
  fontMetrics,
  drawGlyphOn,
  windForNonzero,
  advanceOf,
} from "../../lib/glyph";

const DEFAULT_WORD = "sup computer";
const DEFAULT_TEMP = 0.8; // the shipped default (model card: 84.7% of glyphs parse)
const MAX_GLYPH_TOKENS = 500; // the harness's cap; block 512 less the prompt
const TOP_N = 8;
const WORD_MAX = 24;
const FAMILY = "glyph-nanogpt-1";
const PAD = 64; // em units of air around the word
// the harness's specimen frame (y already flipped): x -64..1088, y -1100..600
const TILE_VIEWBOX = "-64 -1100 1152 1700";

const cleanWord = (s) => s.toLowerCase().replace(/[^a-z ]/g, "").replace(/\s+/g, " ").slice(0, WORD_MAX);
const distinctLetters = (word) => [...new Set(word.replace(/ /g, ""))];
const slug = (word) => word.trim().replace(/ /g, "-") || "word";

function downloadBlob(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// What one generation run became: a glyph, or the reason it isn't one.
function settle(line, ended, stopped, ms, tokens) {
  const base = { line, ms, tokens, glyph: null, error: null };
  if (stopped) return { ...base, status: "bad", error: "stopped before it finished" };
  if (!ended) return { ...base, status: "bad", error: `never ended the line in ${MAX_GLYPH_TOKENS} tokens` };
  try {
    return { ...base, status: "ok", glyph: decodeGlyph(line) };
  } catch (e) {
    return { ...base, status: "bad", error: e instanceof GlyphSyntaxError ? `didn't parse: ${e.message}` : String(e) };
  }
}

// The frame a word sits in: its own extent, the font's vertical metrics.
function wordFrame(layout, metrics) {
  const b = layout.bounds;
  const xMin = Math.min(0, b?.xMin ?? 0) - PAD;
  const xMax = Math.max(layout.width, b?.xMax ?? 0) + PAD;
  const yMax = metrics.ascender + PAD;
  const yMin = metrics.descender - PAD;
  return { xMin, xMax, viewBox: `${xMin} ${-yMax} ${xMax - xMin} ${yMax - yMin}`, width: xMax - xMin, height: yMax - yMin };
}

/** A glyph entry's ink, in em coordinates (the caller flips y). */
function Ink({ entry, x = 0 }) {
  if (!entry) return null;
  const at = x ? `translate(${x} 0)` : undefined;
  if (entry.status === "ok" || (entry.status === "queued" && entry.glyph)) {
    return <path className="glyph__ink" transform={at} d={glyphToSvgPath(entry.glyph)} fillRule="evenodd" />;
  }
  if (entry.status === "drawing") {
    const p = decodeGlyphPartial(entry.line);
    return (
      <g transform={at}>
        {p.contours.length > 0 && (
          <path className="glyph__ink glyph__ink--live" d={glyphToSvgPath(p)} fillRule="evenodd" />
        )}
        {p.open && <path className="glyph__stroke" d={contourToSvgPath(p.open)} />}
      </g>
    );
  }
  return null;
}

function tileTitle(letter, e) {
  if (e.status === "ok") {
    return `${letter} — ${e.tokens} tokens in ${(e.ms / 1000).toFixed(1)} s, advance ${e.glyph.adv}. Click to draw it again.`;
  }
  if (e.status === "bad") return `${letter} — ${e.error}. Click to draw it again.`;
  if (e.status === "drawing") return `${letter} — drawing…`;
  return `${letter} — queued`;
}

export default function GlyphMakerInstrument({ models }) {
  const model = models[0];
  const m = useModel(model);
  const [word, setWord] = useState(DEFAULT_WORD);
  const [temp, setTemp] = useState(DEFAULT_TEMP);
  const [glyphs, setGlyphs] = useState({}); // letter -> { status, line, glyph, error, ms, tokens }
  const [current, setCurrent] = useState(null); // the letter being drawn
  const [drawing, setDrawing] = useState(false); // a batch is running
  const [top, setTop] = useState(null);
  const [view, setView] = useState("demo");
  const [runError, setRunError] = useState(null);
  const [noGpu, setNoGpu] = useState(false);
  const handleRef = useRef(null);
  const cancelRef = useRef(false);

  useEffect(() => setNoGpu(!hasWebGPU()), []);

  const runnable = m.state !== "unpublished" && m.state !== "failed";
  const distinct = distinctLetters(word);
  const undrawn = distinct.filter((l) => glyphs[l]?.status !== "ok");
  const entries = Object.entries(glyphs);
  const tiles = [...entries].sort(([a], [b]) => (a < b ? -1 : 1));
  const okEntries = entries.filter(([, e]) => e.status === "ok");
  const toGo = entries.filter(([, e]) => e.status === "queued").length;

  const draw = async (letters) => {
    if (!runnable || drawing || !letters.length) return;
    setDrawing(true);
    setRunError(null);
    cancelRef.current = false;
    setGlyphs((g) => {
      const next = { ...g };
      for (const l of letters) next[l] = { ...(next[l] ?? {}), status: "queued" };
      return next;
    });
    try {
      for (const letter of letters) {
        if (cancelRef.current) break;
        setCurrent(letter);
        setGlyphs((g) => ({ ...g, [letter]: { status: "drawing", line: letter, glyph: null, error: null } }));
        const t0 = performance.now();
        let line = letter; // the generated line is the letter plus what follows it
        let ended = false;
        let tokens = 0;
        const handle = m.generate(
          {
            prompt: `\n${letter}`,
            maxNewTokens: MAX_GLYPH_TOKENS,
            temp,
            topk: 0,
            stopAt: [BOUNDARY_ID],
            topN: TOP_N,
          },
          (ev) => {
            if (ev.top) setTop(ev.top);
            if (ev.end) {
              ended = true;
              return;
            }
            tokens += 1;
            line += ev.piece;
            const sofar = line;
            setGlyphs((g) => ({ ...g, [letter]: { ...g[letter], line: sofar } }));
          },
        );
        handleRef.current = handle;
        const { stopped } = await handle.done;
        const done = settle(line, ended, stopped, performance.now() - t0, tokens);
        setGlyphs((g) => ({ ...g, [letter]: done }));
        if (stopped) break;
      }
    } catch (e) {
      setRunError(e?.message || String(e));
    } finally {
      handleRef.current = null;
      setCurrent(null);
      setDrawing(false);
      // whatever never got its turn goes back to what it was
      setGlyphs((g) => {
        const next = { ...g };
        for (const [l, e] of Object.entries(next)) {
          if (e.status !== "queued") continue;
          if (e.glyph) next[l] = { ...e, status: "ok" };
          else delete next[l];
        }
        return next;
      });
    }
  };

  const stop = () => {
    cancelRef.current = true;
    handleRef.current?.stop();
  };

  const glyphOf = (ch) => {
    const e = glyphs[ch];
    if (!e) return null;
    if (e.status === "ok" || (e.status === "queued" && e.glyph)) return e.glyph;
    if (e.status === "drawing") {
      const p = decodeGlyphPartial(e.line);
      return p.adv == null ? null : { adv: p.adv, contours: p.contours };
    }
    return null;
  };
  const layout = layoutWord(word, glyphOf);
  const metrics = useMemo(() => fontMetrics(okEntries.map(([, e]) => e.glyph)), [glyphs]); // eslint-disable-line react-hooks/exhaustive-deps
  const frame = wordFrame(layout, metrics);

  const exportSvg = () => {
    const paths = layout.items
      .filter((it) => it.glyph && glyphs[it.ch]?.status === "ok")
      .map((it) => `    <path transform="translate(${it.x} 0)" d="${glyphToSvgPath(it.glyph)}" fill-rule="evenodd"/>`)
      .join("\n");
    const svg =
      `<?xml version="1.0" encoding="UTF-8"?>\n` +
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${frame.viewBox}" width="${frame.width}" height="${frame.height}">\n` +
      `  <title>${word.trim()} — drawn by ${FAMILY}</title>\n` +
      `  <g transform="scale(1,-1)" fill="#000">\n${paths}\n  </g>\n</svg>\n`;
    downloadBlob(new Blob([svg], { type: "image/svg+xml" }), `${FAMILY}-${slug(word)}.svg`);
  };

  const exportOtf = async () => {
    const ot = await import("opentype.js"); // only this page, only on demand
    const { Font, Glyph, Path } = ot.Font ? ot : ot.default;
    const letters = [...okEntries]
      .sort(([a], [b]) => (a < b ? -1 : 1))
      .map(
        ([letter, e]) =>
          new Glyph({
            name: letter,
            unicode: letter.charCodeAt(0),
            advanceWidth: advanceOf(e.glyph),
            path: drawGlyphOn(new Path(), windForNonzero(e.glyph)),
          }),
      );
    const font = new Font({
      familyName: FAMILY,
      styleName: "Regular",
      unitsPerEm: 1024,
      ascender: metrics.ascender,
      descender: metrics.descender,
      designer: "sup computer",
      glyphs: [
        new Glyph({ name: ".notdef", unicode: 0, advanceWidth: 500, path: new Path() }),
        new Glyph({ name: "space", unicode: 32, advanceWidth: SPACE_ADVANCE, path: new Path() }),
        ...letters,
      ],
    });
    font.download(`${FAMILY}-${slug(word)}.otf`);
  };

  const raw = entries
    .map(([, e]) => e.line)
    .filter(Boolean)
    .join("\n");
  const started = entries.length > 0;
  const disabled = !runnable || drawing;
  const slowBackend = m.backend === "wasm" || (m.backend == null && noGpu);

  const status = drawing
    ? m.state === "loading"
      ? "loading the model…"
      : current
        ? `drawing ${current}${toGo ? ` · ${toGo} to go` : ""}`
        : ""
    : undrawn.length && started
      ? `${undrawn.length} letter${undrawn.length === 1 ? "" : "s"} still to draw`
      : "";

  return (
    <div className="instrument glyph">
      {m.state === "unpublished" && (
        <Notice>
          weights not yet published for this release. The instrument lights up the moment
          they land; everything else is already wired.
        </Notice>
      )}
      {m.state === "failed" && <Notice>the model failed to load: {m.error}</Notice>}
      {runnable && slowBackend && (
        <Notice>
          this is the studio&rsquo;s largest model (47.8M parameters), and without WebGPU it
          draws on WebAssembly — slowly. Expect a good while per letter; the tiles draw
          themselves as it goes.
        </Notice>
      )}

      <div className="instrument__row">
        <TextField
          id="glyph-word"
          label="word"
          value={word}
          onChange={(v) => setWord(cleanWord(v))}
          disabled={disabled}
          placeholder={DEFAULT_WORD}
          maxLength={WORD_MAX}
        />
        <RangeField
          id="glyph-temp"
          label="temperature"
          value={temp}
          onChange={setTemp}
          min={0.5}
          max={1.2}
          step={0.05}
          disabled={disabled}
          format={(t) => t.toFixed(2)}
          ticks={[0.8, 1]}
        />
      </div>
      <div className="instrument__controls">
        <RunButton
          generating={drawing}
          loading={m.state === "loading"}
          disabled={!runnable || distinct.length === 0}
          onRun={() => draw(undrawn.length ? undrawn : distinct)}
          onStop={stop}
          label={undrawn.length || !started ? "draw" : "draw again"}
        />
      </div>

      {runError && <p className="instrument__error">error: {runError}</p>}

      <ViewToggle view={view} onChange={setView} demoLabel="specimen" />
      {view === "demo" ? (
        <div className="glyph__view" aria-live="polite">
          {started ? (
            <svg
              className="glyph__word"
              viewBox={frame.viewBox}
              preserveAspectRatio="xMinYMid meet"
              role="img"
              aria-label={`the word “${word.trim()}” set in glyphs drawn by ${FAMILY}`}
            >
              <g transform="scale(1,-1)">
                <line className="glyph__baseline" x1={frame.xMin} x2={frame.xMax} y1={0} y2={0} />
                {layout.items.map((it, i) => {
                  if (it.ch === " ") return null;
                  const e = glyphs[it.ch];
                  if (e && (e.status === "drawing" || e.glyph)) return <Ink key={i} entry={e} x={it.x} />;
                  const bad = e?.status === "bad";
                  return (
                    <g key={i}>
                      <rect
                        className={`glyph__slot${bad ? " glyph__slot--bad" : ""}`}
                        x={it.x + 40}
                        y={0}
                        width={it.width - 80}
                        height={500}
                      />
                      {bad && (
                        <text className="glyph__empty" transform={`translate(${it.x + it.width / 2} 130) scale(1,-1)`} textAnchor="middle">
                          ∅
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>
            </svg>
          ) : (
            <div className="glyph__idle">
              {word.trim() ? `${word.trim()} — ` : ""}
              {distinct.length ? `${distinct.length} letter${distinct.length === 1 ? "" : "s"}, waiting to be drawn.` : "type a word to draw."}
            </div>
          )}
          <p className="glyph__status">{status}</p>

          {tiles.length > 0 && (
            <div className="glyph__specimen" aria-label="the alphabet so far — click a letter to draw it again">
              {tiles.map(([letter, e]) => (
                <button
                  key={letter}
                  type="button"
                  className={`glyph__tile glyph__tile--${e.status}`}
                  onClick={() => draw([letter])}
                  disabled={disabled}
                  title={tileTitle(letter, e)}
                  aria-label={tileTitle(letter, e)}
                >
                  <svg className="glyph__tile-svg" viewBox={TILE_VIEWBOX} aria-hidden="true">
                    <g transform="scale(1,-1)">
                      <line className="glyph__baseline" x1={-64} x2={1088} y1={0} y2={0} />
                      <Ink entry={e} />
                      {e.status === "bad" && (
                        <text className="glyph__empty" transform="translate(512 130) scale(1,-1)" textAnchor="middle">
                          ∅
                        </text>
                      )}
                    </g>
                  </svg>
                  <span className="glyph__tile-letter">{letter}</span>
                  <span className="glyph__tile-note">
                    {e.status === "ok"
                      ? `${e.glyph.adv}`
                      : e.status === "drawing"
                        ? "drawing"
                        : e.status === "bad"
                          ? "redraw"
                          : "queued"}
                  </span>
                </button>
              ))}
            </div>
          )}

          {started && (
            <>
              <p className="glyph__caption">
                Each distinct letter is drawn once, from the prompt <code>↵</code> plus the
                letter. At temperature 0.8 the model finishes about 85 glyphs in every 100;
                the rest never close a contour or never end the line, and show as ∅. Click a
                letter to draw it again — <em>j</em> draws best at 1.0. The number under a
                tile is its advance width, in a 1024-unit em.
              </p>
              <div className="glyph__exports">
                <span className="instrument__label">download</span>
                <button type="button" className="glyph__export" onClick={exportSvg} disabled={!okEntries.length}>
                  the word as SVG
                </button>
                <button type="button" className="glyph__export" onClick={exportOtf} disabled={!okEntries.length}>
                  the alphabet as OTF ({okEntries.length} letter{okEntries.length === 1 ? "" : "s"})
                </button>
              </div>
            </>
          )}
        </div>
      ) : (
        <TokenPane
          prompt=""
          output={raw}
          busy={drawing}
          placeholder="one line per glyph appears here — the letter, its advance width, then M L Q Z drawing verbs whose coordinates are single Braille characters."
        />
      )}

      <DistributionStrip top={top} />
      <BackendLine state={m.state} backend={m.backend} model={model} />
    </div>
  );
}
