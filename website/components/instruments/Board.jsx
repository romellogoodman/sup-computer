"use client";

// daydream's instrument: play the dream, or watch it.
//
// Three boards, one model each (micro 5×5 · regular 8×8 · grand 12×10).
// Regular is playable: you move white, chess.js holds the real position, and
// the model dreams black's reply one character at a time. Before it commits,
// a small character beam over the same context is rendered ON the board —
// the candidate moves it is weighing, legal ones lit, illegal ones struck —
// then the dream runs: a legal move snaps into place, an illegal one is a
// GHOST (the glyph flickers on its target square and dissolves) and the
// model is resampled, up to TRIES times, after which the harness does what
// harness.py does and plays a random legal move.
//
// Micro and Grand are watch-only. The browser has no rules engine for those
// boards (the studio's arbiter is Fairy-Stockfish, a native binary —
// ADR-0021), so the July behaviour stands: a whole game streams from the
// demo prompt and lib/boards.js applies it mechanically — impossible moves
// ghost, unparseable fragments collect in a residue line, a newline in the
// stream restarts the dream. Regular gets the same watch mode next to play.

import { useMemo, useRef, useState } from "react";
import { Chess } from "chess.js";
import { useModel } from "../../lib/instrument/useModel";
import DistributionStrip from "./DistributionStrip";
import TokenPane from "./TokenPane";
import ViewToggle from "./ViewToggle";
import { NumberField, RangeField, RunButton, Notice, BackendLine } from "./Field";
import {
  TIER_ORDER,
  REGULAR_ID,
  TIER_BOARDS,
  GLYPHS,
  FILE_LETTERS,
  pieceName,
  applyGame,
  parseUci8,
  squareOf,
  nameOf,
  gridFromChess,
  isWhite,
} from "../../lib/boards";

const TRIES = 8; // resamples before the harness steps in
const BEAM = { width: 6, branch: 3, depth: 4 }; // 1 + 6 + 6 + 6 forward passes
const GHOST_MS = 520; // a near-miss stays on the board this long before the next try
const TEMP_DEFAULT = 0.9; // harness.py's temperature

const DIAL = [
  [0.2, "sober"],
  [0.55, "drowsy"],
  [0.8, "dreaming"],
  [1.1, "feverish"],
  [1.35, "raving"],
];
const dialWord = (t) => DIAL.reduce((w, [at, word]) => (t >= at ? word : w), DIAL[0][1]);
const pct = (p) => (p >= 0.995 ? "100" : p < 0.005 ? "<1" : String(Math.round(p * 100)));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function softmax(logits, temp) {
  const t = Math.max(temp, 1e-6);
  let max = -Infinity;
  for (let i = 0; i < logits.length; i++) if (logits[i] > max) max = logits[i];
  const out = new Array(logits.length);
  let sum = 0;
  for (let i = 0; i < logits.length; i++) {
    out[i] = Math.exp((logits[i] - max) / t);
    sum += out[i];
  }
  for (let i = 0; i < out.length; i++) out[i] /= sum;
  return out;
}

/** The strip's shape ([{ id, tok, prob }]) from a main-thread distribution. */
const stripOf = (probs, vocab, n = 8) =>
  probs
    .map((prob, id) => ({ id, tok: vocab[id] ?? "", prob }))
    .sort((a, b) => b.prob - a.prob)
    .slice(0, n);

/**
 * The candidate beam: what the model is weighing before it dreams. Step 1
 * takes the top `width` characters; each later step expands every survivor
 * by its top `branch` and keeps the `width` best by cumulative probability,
 * to `depth` characters — one UCI move. Terminators are skipped: a candidate
 * is a move, and the worker serializes calls, so sequential awaits are fine.
 */
async function beam(m, ctxIds, vocab, temp, onFirst) {
  const skip = new Set(vocab.map((ch, i) => (ch === " " || ch === "\n" ? i : -1)).filter((i) => i >= 0));
  const best = (probs, n) =>
    probs
      .map((p, i) => ({ i, p }))
      .filter((x) => !skip.has(x.i))
      .sort((a, b) => b.p - a.p)
      .slice(0, n);
  let items = [{ ids: [], text: "", p: 1 }];
  for (let step = 0; step < BEAM.depth; step++) {
    const next = [];
    for (const it of items) {
      const probs = softmax(await m.forward([...ctxIds, ...it.ids]), temp);
      if (step === 0) onFirst?.(probs);
      for (const { i, p } of best(probs, step === 0 ? BEAM.width : BEAM.branch)) {
        next.push({ ids: [...it.ids, i], text: it.text + vocab[i], p: it.p * p });
      }
    }
    items = next.sort((a, b) => b.p - a.p).slice(0, BEAM.width);
  }
  return items.map(({ text, p }) => ({ move: text, p }));
}

/** Is `tok` a legal move here? Returns the chess.js move object to play, or null. */
function judge(chess, tok) {
  const u = parseUci8(tok);
  if (!u) return null;
  const hit = chess
    .moves({ square: u.from, verbose: true })
    .find((mv) => mv.to === u.to && (!u.promotion || mv.promotion === u.promotion));
  if (!hit) return null;
  // the corpus writes promotions as a 5th char; chess.js needs one named
  return { from: u.from, to: u.to, promotion: hit.promotion ? u.promotion || "q" : undefined };
}

function snapshot(chess) {
  let over = null;
  if (chess.isGameOver()) {
    if (chess.isCheckmate()) over = chess.turn() === "w" ? "checkmate — the dream wins" : "checkmate — you win";
    else if (chess.isStalemate()) over = "stalemate";
    else if (chess.isInsufficientMaterial()) over = "draw — insufficient material";
    else if (chess.isThreefoldRepetition()) over = "draw — threefold repetition";
    else over = "draw — fifty moves";
  }
  return { grid: gridFromChess(chess.board()), turn: chess.turn(), check: chess.inCheck(), over };
}

// ---------------------------------------------------------------------------
// The grid. One renderer for both modes: a letter grid, the ghost, the last
// move, and in play mode the selection, its legal targets, and the overlay.
// ---------------------------------------------------------------------------

function Grid({ tier, grid, ghost, landed, from, selected, targets, overlay, onSquare, live, label }) {
  const { files, ranks, label: size } = tier;
  return (
    <div className="board__scroll">
      <div className={`board__frame board__frame--${size}`}>
        <div className="board__ranks" aria-hidden="true">
          {Array.from({ length: ranks }, (_, r) => (
            <span className="board__coord" key={r}>{ranks - r}</span>
          ))}
        </div>
        <div
          className="board__grid"
          style={{ gridTemplateColumns: `repeat(${files}, var(--board-sq))` }}
          role={live ? "group" : "img"}
          aria-label={label}
        >
          {grid.map((row, r) =>
            row.map((piece, f) => {
              const name = nameOf(f, r, ranks);
              const dark = (r + f) % 2 === 1;
              const isGhost = ghost?.to && ghost.to.r === r && ghost.to.f === f;
              const isLanded = landed && landed.r === r && landed.f === f;
              const isFrom = from && from.r === r && from.f === f;
              const isSel = selected === name;
              const isTarget = Boolean(targets?.includes(name));
              const ov = overlay?.get(name);
              const cls = [
                "board__sq",
                dark && "board__sq--dark",
                live && "board__sq--live",
                isSel && "board__sq--selected",
                isFrom && "board__sq--from",
                isLanded && "board__sq--to",
              ]
                .filter(Boolean)
                .join(" ");
              const inner = (
                <>
                  {ov?.legal > 0 && (
                    <span className="board__cand board__cand--legal" style={{ "--p": ov.legal }} aria-hidden="true" />
                  )}
                  {ov?.illegal > 0 && (
                    <span className="board__cand board__cand--illegal" style={{ "--p": ov.illegal }} aria-hidden="true" />
                  )}
                  {piece && (
                    <span
                      className={`board__pc${isWhite(piece) ? " board__pc--white" : ""}${isLanded ? " board__pc--landed" : ""}`}
                      key={isLanded ? `land${landed.key}` : "pc"}
                    >
                      {GLYPHS[piece] ?? piece}
                    </span>
                  )}
                  {isTarget && (
                    <span className={`board__target${piece ? " board__target--capture" : ""}`} aria-hidden="true" />
                  )}
                  {isGhost && (
                    <span className="board__ghost" key={`g${ghost.idx}`} aria-hidden="true">
                      {ghost.glyph}
                    </span>
                  )}
                </>
              );
              return live ? (
                <button
                  type="button"
                  className={cls}
                  key={name}
                  onClick={() => onSquare(f, r)}
                  aria-label={`${name}, ${pieceName(piece)}${isTarget ? ", legal target" : ""}`}
                  aria-pressed={isSel}
                >
                  {inner}
                </button>
              ) : (
                <div className={cls} key={name}>
                  {inner}
                </div>
              );
            }),
          )}
        </div>
        <span />
        <div className="board__files" aria-hidden="true">
          {Array.from({ length: files }, (_, f) => (
            <span className="board__coord" key={f}>{FILE_LETTERS[f]}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

// The ghost shows the glyph that TRIED to move (whatever sits on the source
// square), or a faint pawn if the source was empty — the dream moved a piece
// that isn't there.
function ghostGlyph(from, grid) {
  const p = from && grid[from.r]?.[from.f];
  return p ? GLYPHS[p] ?? p : "♟";
}

// One entry of the move list: who played it, and how many tries it took.
function Move({ mv }) {
  const title =
    mv.by === "harness"
      ? `the harness's move: the model missed ${TRIES} times`
      : mv.by === "model"
        ? `the model's move, legal on try ${mv.tries}`
        : "your move";
  return (
    <span className={`board__move board__move--${mv.by}`} title={title}>
      {mv.uci}
      {mv.by === "model" && mv.tries > 1 && <sup className="board__move-tries">{mv.tries}</sup>}
      {mv.by === "harness" && <sup className="board__move-tries">†</sup>}
    </span>
  );
}

// ---------------------------------------------------------------------------

export default function BoardInstrument({ models }) {
  const tiers = useMemo(
    () => TIER_ORDER.map((id) => models.find((x) => x.id === id)).filter(Boolean),
    [models],
  );
  const [tierId, setTierId] = useState(() => (tiers.some((t) => t.id === REGULAR_ID) ? REGULAR_ID : tiers[0]?.id));
  const model = tiers.find((t) => t.id === tierId) || null;
  const tier = TIER_BOARDS[tierId];
  const m = useModel(model);

  const [mode, setMode] = useState(tier?.playable ? "play" : "watch");
  const [view, setView] = useState("demo");
  const [temp, setTemp] = useState(TEMP_DEFAULT);
  const [watchMax, setWatchMax] = useState(tier?.maxNewTokens ?? 480);
  const [top, setTop] = useState(null);
  const [runError, setRunError] = useState(null);

  // watch mode: the raw stream
  const [output, setOutput] = useState("");
  const watchHandle = useRef(null);

  // play mode: chess.js holds the position; everything else is the render
  const chessRef = useRef(null);
  if (!chessRef.current) chessRef.current = new Chess();
  const [pos, setPos] = useState(() => snapshot(chessRef.current));
  const [moves, setMoves] = useState([]); // UCI history — the model's context
  const [log, setLog] = useState([]); // [{ uci, by: "you"|"model"|"harness", tries }]
  const [last, setLast] = useState(null); // { from, to, key }
  const [selected, setSelected] = useState(null);
  const [targets, setTargets] = useState([]);
  const [ghost, setGhost] = useState(null); // { from, to, glyph, idx }
  const [attempts, setAttempts] = useState([]); // this turn's near-misses
  const [misses, setMisses] = useState(0); // the game's
  const [cands, setCands] = useState(null); // the overlay: [{ move, p, legal, played, dreamt }]
  const [phase, setPhase] = useState("idle"); // idle | weighing | dreaming | harness
  const [tryN, setTryN] = useState(0);
  const [raw, setRaw] = useState(""); // every string the model emitted this turn
  const epochRef = useRef(0); // bumped by new game / tier switch; stale loops bail
  const ghostSeq = useRef(0);
  const vocabRef = useRef({ id: null, chars: null });

  const busy = m.state === "loading" || m.generating;
  const runnable = m.state !== "unpublished" && m.state !== "failed";
  const playing = mode === "play" && tier?.playable;
  const thinking = phase !== "idle";

  // ---- resets --------------------------------------------------------------

  const resetPlay = () => {
    epochRef.current += 1;
    m.stop();
    chessRef.current = new Chess();
    setPos(snapshot(chessRef.current));
    setMoves([]);
    setLog([]);
    setLast(null);
    setSelected(null);
    setTargets([]);
    setGhost(null);
    setAttempts([]);
    setMisses(0);
    setCands(null);
    setPhase("idle");
    setTryN(0);
    setRaw("");
    setTop(null);
    setRunError(null);
  };

  const switchTier = (id) => {
    if (id === tierId) return;
    watchHandle.current?.stop();
    resetPlay();
    setOutput("");
    setTierId(id);
    const next = TIER_BOARDS[id];
    setMode(next?.playable ? "play" : "watch");
    setWatchMax(next?.maxNewTokens ?? 480);
  };

  const switchMode = (next) => {
    if (next === mode) return;
    if (next === "play" && !tier?.playable) return;
    watchHandle.current?.stop();
    resetPlay();
    setOutput("");
    setMode(next);
  };

  // ---- watch: stream a whole game from the demo prompt ---------------------

  const watchPrompt = model?.demo?.prompt || "";

  const runWatch = async () => {
    if (!runnable || busy) return;
    setOutput("");
    setTop(null);
    setRunError(null);
    const handle = m.generate(
      { prompt: watchPrompt, maxNewTokens: watchMax, temp, topk: 0, topN: 8 },
      (ev) => {
        if (ev.piece) setOutput((s) => s + ev.piece);
        if (ev.top) setTop(ev.top);
      },
    );
    watchHandle.current = handle;
    try {
      await handle.done;
    } catch (e) {
      setRunError(e?.message || String(e));
    }
  };

  const watched = useMemo(() => {
    if (!tier) return null;
    const text = output || busy ? watchPrompt + output : "";
    const dreams = text.split(/\n+/);
    const current = dreams[dreams.length - 1] ?? "";
    const tokens = current.trim().split(/\s+/).filter(Boolean);
    return { ...applyGame(tier, tokens), dream: dreams.length, started: Boolean(text) };
  }, [output, busy, watchPrompt, tier]);

  // ---- play: the human's move ----------------------------------------------

  const onSquare = (f, r) => {
    if (!playing || thinking || pos.over || pos.turn !== "w") return;
    const chess = chessRef.current;
    const name = nameOf(f, r, 8);
    if (selected && targets.includes(name)) {
      humanMove(selected, name);
      return;
    }
    const piece = pos.grid[r][f];
    if (piece && isWhite(piece)) {
      setSelected(name);
      setTargets(chess.moves({ square: name, verbose: true }).map((mv) => mv.to));
      m.ensure().catch(() => {}); // start the download on the first touch
      return;
    }
    setSelected(null);
    setTargets([]);
  };

  const humanMove = (from, to) => {
    const chess = chessRef.current;
    const hit = chess.moves({ square: from, verbose: true }).find((mv) => mv.to === to);
    if (!hit) return;
    const mv = chess.move({ from, to, promotion: hit.promotion ? "q" : undefined });
    const uci = mv.from + mv.to + (mv.promotion || "");
    const history = [...moves, uci];
    setMoves(history);
    setLog((l) => [...l, { uci, by: "you" }]);
    setLast({ from: squareOf(mv.from, 8, 8), to: squareOf(mv.to, 8, 8), key: history.length });
    setSelected(null);
    setTargets([]);
    setCands(null);
    setAttempts([]);
    setGhost(null);
    setRaw("");
    setRunError(null);
    const snap = snapshot(chess);
    setPos(snap);
    if (!snap.over) dream(history);
  };

  // ---- play: the model's reply ---------------------------------------------

  const getVocab = async () => {
    if (vocabRef.current.id === model.id && vocabRef.current.chars) return vocabRef.current.chars;
    const n = model.tokenizer?.vocab_size || 0;
    const chars = Array.from(await m.decode(Array.from({ length: n }, (_, i) => i)));
    vocabRef.current = { id: model.id, chars };
    return chars;
  };

  const dream = async (history) => {
    const epoch = epochRef.current;
    const stale = () => epochRef.current !== epoch;
    const chess = chessRef.current;
    const grid = gridFromChess(chess.board());
    setPhase("weighing");
    try {
      const vocab = await getVocab();
      const stopAt = [vocab.indexOf(" "), vocab.indexOf("\n")].filter((i) => i >= 0);
      const ctxIds = await m.encode(history.join(" ") + " ");
      if (stale()) return;

      // 1. the overlay — what it is weighing, before it dreams
      const items = await beam(m, ctxIds, vocab, temp, (probs) => {
        if (!stale()) setTop(stripOf(probs, vocab));
      });
      if (stale()) return;
      setCands(items.map((c) => ({ ...c, legal: Boolean(judge(chess, c.move)), played: false, dreamt: 0 })));

      // 2. the dream — resample on an illegal move, up to TRIES
      setPhase("dreaming");
      const tried = [];
      let landed = null;
      for (let t = 1; t <= TRIES; t++) {
        setTryN(t);
        const run = m.generate(
          { ids: ctxIds, maxNewTokens: 6, temp, topk: 0, stopAt, topN: 8 },
          (ev) => {
            if (stale()) return;
            if (ev.piece) setRaw((s) => s + ev.piece);
            if (ev.top) setTop(ev.top);
          },
        );
        const res = await run.done;
        if (stale()) return;
        setRaw((s) => s + " ");
        const tok = res.text;
        const legal = judge(chess, tok);
        if (legal) {
          landed = { ...legal, tries: t };
          break;
        }
        tried.push(tok);
        const u = parseUci8(tok);
        const from = u ? squareOf(u.from, 8, 8) : null;
        const to = u ? squareOf(u.to, 8, 8) : null;
        const idx = ++ghostSeq.current;
        setGhost(to ? { from, to, glyph: ghostGlyph(from, grid), idx } : null);
        setAttempts((a) => [...a, { tok: tok || "∅", idx }]);
        setMisses((n) => n + 1);
        await sleep(GHOST_MS);
        if (stale()) return;
      }

      // 3. the harness: eight misses, a random legal move — harness.py's rule
      let by = "model";
      if (!landed) {
        setPhase("harness");
        const legal = chess.moves({ verbose: true });
        const pick = legal[Math.floor(Math.random() * legal.length)];
        landed = { from: pick.from, to: pick.to, promotion: pick.promotion, tries: TRIES };
        by = "harness";
        await sleep(GHOST_MS);
        if (stale()) return;
      }

      const mv = chess.move({ from: landed.from, to: landed.to, promotion: landed.promotion });
      const uci = mv.from + mv.to + (mv.promotion || "");
      setMoves((h) => [...h, uci]);
      setLog((l) => [...l, { uci, by, tries: landed.tries }]);
      setLast({ from: squareOf(mv.from, 8, 8), to: squareOf(mv.to, 8, 8), key: history.length + 1 });
      setCands((cs) =>
        cs &&
        cs.map((c) => ({
          ...c,
          played: by === "model" && uci.startsWith(c.move),
          dreamt: tried.filter((x) => x === c.move).length,
        })),
      );
      setPos(snapshot(chess));
    } catch (e) {
      if (!stale()) setRunError(e?.message || String(e));
    } finally {
      if (!stale()) {
        setPhase("idle");
        setTryN(0);
      }
    }
  };

  // the overlay, per destination square: legal and illegal mass kept apart
  const overlay = useMemo(() => {
    if (!cands) return null;
    const by = new Map();
    for (const c of cands) {
      const u = parseUci8(c.move);
      if (!u) continue;
      const cur = by.get(u.to) || { legal: 0, illegal: 0 };
      cur[c.legal ? "legal" : "illegal"] += c.p;
      by.set(u.to, cur);
    }
    return by;
  }, [cands]);

  if (!tier || !model) return <Notice>no daydream release is registered yet.</Notice>;

  // ---- render ---------------------------------------------------------------

  const context = moves.join(" ") + (moves.length ? " " : "");
  const disabled = !runnable || busy;

  let status;
  if (playing) {
    if (pos.over) status = pos.over;
    else if (m.state === "loading") status = "downloading the model to your browser…";
    else if (phase === "weighing") status = "the model is weighing its candidates…";
    else if (phase === "dreaming") status = `dreaming… try ${tryN} of ${TRIES}`;
    else if (phase === "harness") status = `${TRIES} near-misses — the harness plays a random legal move`;
    else if (moves.length === 0) status = "your move — you play white; touch a piece";
    else status = pos.check ? "check — your move" : "your move";
  }

  const pairs = [];
  for (let i = 0; i < log.length; i += 2) pairs.push([log[i], log[i + 1]]);

  return (
    <div className="instrument board">
      {m.state === "unpublished" && (
        <Notice>
          weights not yet published for this release — the instrument lights up when they land.
        </Notice>
      )}
      {m.state === "failed" && <Notice>the model failed to load: {m.error}</Notice>}

      <div className="instrument__chips" role="group" aria-label="board size">
        <span className="instrument__label">board</span>
        {tiers.map((t) => {
          const b = TIER_BOARDS[t.id];
          return (
            <button
              key={t.id}
              type="button"
              className={`instrument__chip${t.id === tierId ? " instrument__chip--on" : ""}`}
              onClick={() => switchTier(t.id)}
              aria-pressed={t.id === tierId}
            >
              {b.label} <span className="board__chip-size">{b.size}</span>
            </button>
          );
        })}
      </div>
      <div className="instrument__chips" role="group" aria-label="mode">
        <span className="instrument__label">mode</span>
        <button
          type="button"
          className={`instrument__chip${mode === "play" ? " instrument__chip--on" : ""}`}
          onClick={() => switchMode("play")}
          disabled={!tier.playable}
          aria-pressed={mode === "play"}
          title={tier.playable ? undefined : "no rules engine in the browser for this board"}
        >
          play
        </button>
        <button
          type="button"
          className={`instrument__chip${mode === "watch" ? " instrument__chip--on" : ""}`}
          onClick={() => switchMode("watch")}
          aria-pressed={mode === "watch"}
        >
          watch
        </button>
      </div>
      <p className="board__caption">
        You play white on the regular board; chess.js referees the 8×8. Micro and grand are
        watch-only: no rules engine runs in the browser for a 5×5 or a 12×10 board, so those boards
        render the dream without refereeing it. The studio&rsquo;s arbiter, Fairy-Stockfish, is a
        native binary.
      </p>

      <div className="instrument__controls">
        <RangeField
          id="board-temp"
          label="temperature"
          value={temp}
          onChange={setTemp}
          min={0.2}
          max={1.6}
          step={0.05}
          disabled={disabled || thinking}
          format={(t) => `${t.toFixed(2)} · ${dialWord(t)}`}
          ticks={[0.2, 0.55, 0.9, 1.1, 1.35]}
        />
        {mode === "watch" ? (
          <>
            <NumberField label="max tokens" value={watchMax} onChange={setWatchMax} min={1} max={4000} disabled={disabled} />
            <RunButton
              generating={m.generating}
              loading={m.state === "loading"}
              disabled={!runnable}
              onRun={runWatch}
              onStop={() => watchHandle.current?.stop()}
              label="dream"
            />
          </>
        ) : (
          <button type="button" className="instrument__button" onClick={resetPlay} disabled={!runnable}>
            new game
          </button>
        )}
      </div>

      {runError && <p className="instrument__error">error: {runError}</p>}

      <ViewToggle view={view} onChange={setView} demoLabel="board" />

      {view === "demo" ? (
        playing ? (
          <div className="board__play" aria-live="polite">
            <Grid
              tier={tier}
              grid={pos.grid}
              ghost={ghost}
              landed={last ? { ...last.to, key: last.key } : null}
              from={last?.from}
              selected={selected}
              targets={targets}
              overlay={selected ? null : overlay}
              onSquare={onSquare}
              live
              label="the board — you play white"
            />
            <div className="board__meta">
              <span className="board__status">{status}</span>
              <span>{moves.length} plies</span>
              <span>{misses} near-misses</span>
              {thinking && <span className="instrument__cursor">▮</span>}
            </div>
            {attempts.length > 0 && (
              <div className="board__residue" aria-hidden="true">
                {attempts.slice(-8).map((a) => (
                  <span className="board__residue-tok" key={a.idx}>{a.tok}</span>
                ))}
              </div>
            )}
            {cands && (
              <table className="board__cands">
                <caption className="board__cands-caption">
                  what the model weighed before it dreamt — a {BEAM.depth}-character beam over its own
                  next-character distribution
                </caption>
                <thead>
                  <tr>
                    <th scope="col">move</th>
                    <th scope="col">probability</th>
                    <th scope="col">legal</th>
                  </tr>
                </thead>
                <tbody>
                  {cands.map((c) => (
                    <tr
                      key={c.move}
                      className={`board__cand-row board__cand-row--${c.legal ? "legal" : "illegal"}${c.played ? " board__cand-row--played" : ""}`}
                    >
                      <td className="board__cand-move">{c.move}</td>
                      <td className="board__cand-prob">
                        <span
                          className={`board__cand-bar${c.legal ? " board__cand-bar--legal" : ""}`}
                          style={{ "--p": `${Math.max(1, Math.round(c.p * 100))}%` }}
                        />
                        {pct(c.p)}%
                      </td>
                      <td className="board__cand-flag">
                        {c.legal ? "legal" : "illegal"}
                        {c.played ? " · played" : c.dreamt ? ` · dreamt ×${c.dreamt}` : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {log.length > 0 && (
              <>
                <ol className="board__moves" aria-label="the moves so far">
                  {pairs.map(([w, b], i) => (
                    <li className="board__ply" key={i}>
                      <span className="board__ply-n">{i + 1}.</span> <Move mv={w} />
                      {b && (
                        <>
                          {" "}
                          <Move mv={b} />
                        </>
                      )}
                    </li>
                  ))}
                </ol>
                <p className="board__legend">
                  <sup>n</sup> tries before a legal move landed · <sup>†</sup> the harness&rsquo;s random legal move after {TRIES} misses
                </p>
              </>
            )}
          </div>
        ) : (
          <div className="board__watch" aria-live="polite">
            {(() => {
              const w = watched;
              const lastGhost = w.ghosts[w.ghosts.length - 1];
              const lastPlay = w.plays[w.plays.length - 1];
              return (
                <>
                  <Grid
                    tier={tier}
                    grid={w.board}
                    ghost={lastGhost ? { ...lastGhost, glyph: ghostGlyph(lastGhost.from, w.board) } : null}
                    landed={lastPlay ? { ...lastPlay.to, key: lastPlay.idx } : null}
                    from={lastPlay?.from}
                    label={`the ${tier.size} board — watching the dream`}
                  />
                  <div className="board__meta">
                    <span>{w.started ? `dream ${w.dream}` : "the board waits for a dream"}</span>
                    <span>{w.plays.length} moves landed</span>
                    <span>{w.ghosts.length + w.residue.length} near-misses</span>
                    {busy && <span className="instrument__cursor">▮</span>}
                  </div>
                  {(w.ghosts.length > 0 || w.residue.length > 0) && (
                    <div className="board__residue" aria-hidden="true">
                      {[...w.ghosts.map((g) => g.tok), ...w.residue.map((x) => x.tok)]
                        .slice(-6)
                        .map((tok, i) => (
                          <span className="board__residue-tok" key={`${tok}-${i}`}>{tok}</span>
                        ))}
                    </div>
                  )}
                </>
              );
            })()}
          </div>
        )
      ) : playing ? (
        <TokenPane
          prompt={context}
          output={raw}
          busy={thinking}
          placeholder="every string the model emits on its turn appears here, in order — the raw dream; the move history is its prompt."
        />
      ) : (
        <TokenPane
          prompt={watchPrompt}
          output={output}
          busy={busy}
          placeholder="the game appears here as UCI moves."
        />
      )}

      <DistributionStrip top={top} label="next char" hint="the model's next-character candidates appear here as it dreams" />
      <BackendLine state={m.state} backend={m.backend} model={model} extra={`${tier.size} board`} />
    </div>
  );
}
