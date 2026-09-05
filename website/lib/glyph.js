// The glyph codec's decode side — a faithful JS port of
// projects/glyph/models/glyph-nanogpt-1/codec.py (ADR-0027), plus the few
// pure helpers the font maker needs on top (bounds, word layout, opentype
// path commands). No ORT, no React: the instrument (components/instruments/
// GlyphMaker.jsx) and the node test (glyph.test.mjs) import it alike.
//
// One glyph is one line:
//
//     <letter><adv> M <x><y> [L <x><y> | Q <cx><cy> <x><y>]* Z ... \n
//
// (spaces for readability only — every symbol is exactly one char). The
// alphabet is FIXED and explicit, never derived from a corpus — letters a-z,
// verbs M L Q Z, 96 Braille coordinate chars U+2800..U+285F, the newline —
// 127 chars whose order is also the tokenizer's id order (ADR-0012).
// Geometry: a 1024-unit em, y-up, baseline y=0; a coordinate char is one
// 16-unit grid position spanning em units -512..1008 (bucket b <-> -512 +
// 16·b); contours are closed and must be filled even-odd.
//
// decodeGlyph is the strict grammar parser codec.decode_glyph is — the same
// checks in the same order with the same messages (glyph.test.mjs pins them
// to Python-produced fixtures) — so it doubles as the validity check on
// model output, exactly as the sampling harness uses it. decodeGlyphPartial
// is the one addition the Python side doesn't have: a tolerant read of a
// line still being generated, so a tile can draw itself as tokens land.

// --- the fixed alphabet ------------------------------------------------------

export const LETTERS = "abcdefghijklmnopqrstuvwxyz";
export const VERBS = "MLQZ";
export const N_BUCKETS = 96;
export const COORD_BASE = 0x2800; // Braille Patterns block: 96 contiguous printable chars
export const COORDS = Array.from({ length: N_BUCKETS }, (_, b) => String.fromCharCode(COORD_BASE + b)).join("");
export const BOUNDARY = "\n";
export const ALPHABET = LETTERS + VERBS + COORDS + BOUNDARY; // 127 chars, fixed order

export const EM = 1024;
export const GRID = 16;
export const COORD_MIN = -512; // bucket 0 -> -512; bucket 95 -> +1008

/** The glyph boundary's token id — ALPHABET's order is the vocab's (126). */
export const BOUNDARY_ID = ALPHABET.indexOf(BOUNDARY);

export const isLetter = (ch) => typeof ch === "string" && ch.length === 1 && LETTERS.includes(ch);

export function isCoord(ch) {
  if (typeof ch !== "string" || ch.length !== 1) return false;
  const c = ch.charCodeAt(0);
  return c >= COORD_BASE && c < COORD_BASE + N_BUCKETS;
}

/** Coordinate char -> em units (codec.unbucket). */
export function unbucket(ch) {
  return COORD_MIN + GRID * (ch.codePointAt(0) - COORD_BASE);
}

// --- parse ---------------------------------------------------------------------

export class GlyphSyntaxError extends Error {
  constructor(message) {
    super(message);
    this.name = "GlyphSyntaxError";
  }
}

// Python's repr() of a one-char string, so "unexpected char" messages match
// codec.py byte for byte.
function pyRepr(ch) {
  const esc = { "\n": "\\n", "\r": "\\r", "\t": "\\t", "\\": "\\\\" };
  if (ch in esc) return `'${esc[ch]}'`;
  if (ch === "'") return `"'"`;
  const c = ch.codePointAt(0);
  if (c < 0x20 || c === 0x7f) return `'\\x${c.toString(16).padStart(2, "0")}'`;
  return `'${ch}'`;
}

/**
 * Strict parse of one line -> { letter, adv, contours } where contours are
 * [[verb, [x, y], ...], ...] in em units (["M", p] | ["L", p] | ["Q", c, p]).
 * Throws GlyphSyntaxError — this is the grammar validity check for model
 * output too. Indexes count code points, as Python's do.
 */
export function decodeGlyph(line) {
  const s = Array.from(line ?? "");
  if (s.length < 2 || !isLetter(s[0]) || !isCoord(s[1])) {
    throw new GlyphSyntaxError("bad header (letter + advance expected)");
  }
  const letter = s[0];
  const adv = unbucket(s[1]);
  let i = 2;
  const contours = [];
  let cur = null;

  const takePt = () => {
    if (i + 1 >= s.length || !(isCoord(s[i]) && isCoord(s[i + 1]))) {
      throw new GlyphSyntaxError(`coordinate pair expected at ${i}`);
    }
    const p = [unbucket(s[i]), unbucket(s[i + 1])];
    i += 2;
    return p;
  };

  while (i < s.length) {
    const v = s[i];
    i += 1;
    if (v === "M") {
      if (cur !== null) throw new GlyphSyntaxError("M inside an open contour");
      cur = [["M", takePt()]];
    } else if (v === "L") {
      if (cur === null) throw new GlyphSyntaxError("L outside a contour");
      cur.push(["L", takePt()]);
    } else if (v === "Q") {
      if (cur === null) throw new GlyphSyntaxError("Q outside a contour");
      const c = takePt();
      const p = takePt();
      cur.push(["Q", c, p]);
    } else if (v === "Z") {
      if (cur === null || cur.length < 2) throw new GlyphSyntaxError("Z on an empty contour");
      contours.push(cur);
      cur = null;
    } else {
      throw new GlyphSyntaxError(`unexpected char ${pyRepr(v)} at ${i - 1}`);
    }
  }
  if (cur !== null) throw new GlyphSyntaxError("unclosed contour at end of line");
  if (!contours.length) throw new GlyphSyntaxError("no contours");
  return { letter, adv, contours };
}

/**
 * Tolerant read of a line mid-generation: everything parseable so far.
 * Never throws. Returns { letter, adv, contours, open } — `contours` the
 * closed ones, `open` the contour still being drawn (or null). Stops at the
 * first token the strict grammar would reject, so a finished line reads the
 * same as decodeGlyph on it.
 */
export function decodeGlyphPartial(line) {
  const s = Array.from(line ?? "");
  const out = { letter: null, adv: null, contours: [], open: null };
  if (s.length < 1 || !isLetter(s[0])) return out;
  out.letter = s[0];
  if (s.length < 2 || !isCoord(s[1])) return out;
  out.adv = unbucket(s[1]);
  let i = 2;
  let cur = null;
  const pt = () => {
    if (i + 1 >= s.length || !(isCoord(s[i]) && isCoord(s[i + 1]))) return null;
    const p = [unbucket(s[i]), unbucket(s[i + 1])];
    i += 2;
    return p;
  };
  while (i < s.length) {
    const v = s[i];
    i += 1;
    if (v === "M") {
      if (cur !== null) break;
      const p = pt();
      if (!p) break;
      cur = [["M", p]];
    } else if (v === "L") {
      if (cur === null) break;
      const p = pt();
      if (!p) break;
      cur.push(["L", p]);
    } else if (v === "Q") {
      if (cur === null) break;
      const c = pt();
      if (!c) break;
      const p = pt();
      if (!p) break;
      cur.push(["Q", c, p]);
    } else if (v === "Z") {
      if (cur === null || cur.length < 2) break;
      out.contours.push(cur);
      cur = null;
    } else {
      break;
    }
  }
  out.open = cur;
  return out;
}

// --- render ----------------------------------------------------------------------

/** One contour's segments as SVG path data, no closing Z. */
export function contourToSvgPath(contour) {
  let d = "";
  for (const seg of contour) {
    if (seg[0] === "M") d += `M${seg[1][0]} ${seg[1][1]}`;
    else if (seg[0] === "L") d += `L${seg[1][0]} ${seg[1][1]}`;
    else d += `Q${seg[1][0]} ${seg[1][1]} ${seg[2][0]} ${seg[2][1]}`;
  }
  return d;
}

/**
 * Decoded glyph -> SVG path data in em coordinates (y-up; the renderer
 * applies the flip). Every contour closes with Z; fill-rule must be evenodd.
 * Byte-identical to codec.glyph_to_svg_path.
 */
export function glyphToSvgPath(decoded) {
  let d = "";
  for (const contour of decoded.contours) d += `${contourToSvgPath(contour)}Z`;
  return d;
}

/**
 * Bounds over every point a glyph names, control points included — a
 * quadratic never leaves its control hull, so this is a safe superset of
 * the ink. Null for a glyph with no contours.
 */
export function glyphBounds(decoded) {
  let xMin = Infinity;
  let yMin = Infinity;
  let xMax = -Infinity;
  let yMax = -Infinity;
  const see = ([x, y]) => {
    if (x < xMin) xMin = x;
    if (x > xMax) xMax = x;
    if (y < yMin) yMin = y;
    if (y > yMax) yMax = y;
  };
  for (const contour of decoded.contours ?? []) {
    for (const seg of contour) {
      see(seg[1]);
      if (seg[0] === "Q") see(seg[2]);
    }
  }
  return xMin === Infinity ? null : { xMin, yMin, xMax, yMax };
}

/**
 * Decoded glyph -> opentype.js path commands ({ type: "M"|"L"|"Q"|"Z", … }),
 * the shape of opentype.Path#commands. Y stays up: font units share the
 * codec's orientation, so no flip here.
 */
export function glyphToPathCommands(decoded) {
  const cmds = [];
  for (const contour of decoded.contours) {
    for (const seg of contour) {
      if (seg[0] === "M") cmds.push({ type: "M", x: seg[1][0], y: seg[1][1] });
      else if (seg[0] === "L") cmds.push({ type: "L", x: seg[1][0], y: seg[1][1] });
      else cmds.push({ type: "Q", x1: seg[1][0], y1: seg[1][1], x: seg[2][0], y: seg[2][1] });
    }
    cmds.push({ type: "Z" });
  }
  return cmds;
}

/**
 * Draw a decoded glyph onto anything with the canvas path verbs — an
 * opentype.Path, a CanvasRenderingContext2D, a Path2D. Returns the target.
 */
export function drawGlyphOn(path, decoded) {
  for (const c of glyphToPathCommands(decoded)) {
    if (c.type === "M") path.moveTo(c.x, c.y);
    else if (c.type === "L") path.lineTo(c.x, c.y);
    else if (c.type === "Q") path.quadraticCurveTo(c.x1, c.y1, c.x, c.y);
    else if (path.closePath) path.closePath();
    else path.close();
  }
  return path;
}

// --- a word ------------------------------------------------------------------------

export const SPACE_ADVANCE = 300; // em units: the gap a space leaves in a word
export const MISSING_ADVANCE = 500; // em units: the slot an undrawn or failed letter holds

/** A drawn glyph's advance as a layout width: never negative. */
export const advanceOf = (decoded) => Math.max(0, decoded.adv);

/**
 * Lay a word out on one baseline: each letter placed at the sum of the
 * advances before it, spaces a fixed gap, letters without a glyph a fixed
 * slot. `glyphOf(letter)` returns a decoded glyph or null.
 * Returns { items: [{ ch, x, width, glyph }], width, bounds } — bounds over
 * the placed glyphs' ink (null when nothing is drawn).
 */
export function layoutWord(word, glyphOf, { space = SPACE_ADVANCE, missing = MISSING_ADVANCE } = {}) {
  const items = [];
  let x = 0;
  let bounds = null;
  for (const ch of word) {
    if (ch === " ") {
      items.push({ ch, x, width: space, glyph: null });
      x += space;
      continue;
    }
    const glyph = glyphOf(ch) ?? null;
    const width = glyph ? advanceOf(glyph) : missing;
    items.push({ ch, x, width, glyph });
    if (glyph) {
      const b = glyphBounds(glyph);
      if (b) {
        bounds = bounds
          ? {
              xMin: Math.min(bounds.xMin, x + b.xMin),
              yMin: Math.min(bounds.yMin, b.yMin),
              xMax: Math.max(bounds.xMax, x + b.xMax),
              yMax: Math.max(bounds.yMax, b.yMax),
            }
          : { xMin: x + b.xMin, yMin: b.yMin, xMax: x + b.xMax, yMax: b.yMax };
      }
    }
    x += width;
  }
  return { items, width: x, bounds };
}

export const DEFAULT_ASCENDER = 800;
export const DEFAULT_DESCENDER = -250;

/**
 * Vertical metrics for a font built from these glyphs: the defaults,
 * widened to cover any glyph that overshoots them (a font never clips its
 * own letters).
 */
export function fontMetrics(glyphs) {
  let ascender = DEFAULT_ASCENDER;
  let descender = DEFAULT_DESCENDER;
  for (const g of glyphs) {
    const b = glyphBounds(g);
    if (!b) continue;
    if (b.yMax > ascender) ascender = b.yMax;
    if (b.yMin < descender) descender = b.yMin;
  }
  return { ascender, descender };
}

// --- winding, for fonts ---------------------------------------------------------

// The codec winds every contour clockwise and leans on even-odd fill, so
// direction carries no information in a line. OpenType rasterizers fill
// nonzero: a counter wound the same way as its bowl fills solid. Before a
// glyph goes into a font, each contour is re-wound by nesting depth — even
// depth clockwise, odd depth counter-clockwise — which reproduces even-odd
// for nested, non-overlapping contours (overlapping ones, which the model
// does emit now and then, differ slightly between the SVG and the font).

const onCurvePoints = (contour) => contour.map((seg) => (seg[0] === "Q" ? seg[2] : seg[1]));

function signedArea(pts) {
  let a = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x0, y0] = pts[i];
    const [x1, y1] = pts[(i + 1) % pts.length];
    a += x0 * y1 - x1 * y0;
  }
  return a / 2;
}

function pointInPolygon([px, py], pts) {
  let inside = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, yi] = pts[i];
    const [xj, yj] = pts[j];
    if (yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/** The same closed contour traversed the other way (Z's straight edge kept). */
export function reverseContour(contour) {
  const n = contour.length - 1; // edges after the M
  if (n < 1) return contour.slice();
  const out = [["M", contour[n][0] === "Q" ? contour[n][2] : contour[n][1]]];
  for (let i = n; i >= 1; i--) {
    const prev = contour[i - 1][0] === "Q" ? contour[i - 1][2] : contour[i - 1][1];
    if (contour[i][0] === "Q") out.push(["Q", contour[i][1], prev]);
    else out.push(["L", prev]);
  }
  return out;
}

/**
 * A copy of the glyph wound for nonzero fill: contours at even nesting
 * depth clockwise (negative signed area in y-up coordinates), odd depth
 * counter-clockwise. Even-odd rendering of the result is unchanged.
 */
export function windForNonzero(decoded) {
  const polys = decoded.contours.map(onCurvePoints);
  const contours = decoded.contours.map((contour, i) => {
    let depth = 0;
    for (let j = 0; j < polys.length; j++) {
      if (j !== i && polys[j].length >= 3 && pointInPolygon(polys[i][0], polys[j])) depth += 1;
    }
    const area = signedArea(polys[i]);
    const wantClockwise = depth % 2 === 0;
    const isClockwise = area < 0;
    return area === 0 || isClockwise === wantClockwise ? contour : reverseContour(contour);
  });
  return { ...decoded, contours };
}
