"""
codec.py -- glyph outlines <-> one-char-per-token text (ADR-0027).

One glyph is one line:

    <letter><adv> M <x><y> [L <x><y> | Q <cx><cy> <x><y>]* Z ... \\n

(spaces shown for readability only -- every symbol is exactly one char).

The alphabet is FIXED and explicit -- never derived from a corpus with
set(data) -- so every dataset (26 specialists + omni) shares one vocab and
one meta.pkl shape, and all arms score the same test file identically:

    letters      a-z                       glyph identity / conditioning (26)
    verbs        M L Q Z                   move, line, quadratic, close  (4)
    coordinates  U+2800..U+285F (Braille)  96 grid buckets               (96)
    boundary     \\n                        one glyph per line            (1)
                                                                   total 127

Geometry: the em is normalized to 1024 (scale 1024/UPM, y-up, baseline y=0),
coordinates quantized to a 16-unit grid spanning em units -512..1008 --
bucket b <-> unit -512 + 16*b. Coordinates never decompose into digits: one
char is one grid position. Cubic (CFF) outlines are converted to quadratic
via cu2qu so a single curve verb suffices.

Canonical form (applied after quantization, so encode(decode(encode(x))) is
stable): all contours wound clockwise and rendered with the even-odd fill
rule (direction carries no fill information, so it can be normalized away);
each contour starts at its lowest-then-leftmost on-curve point; contours
ordered largest-area first. No augmentation lives here.

decode() is a strict grammar parser -- it doubles as the validity check the
sampling harness uses on model output.
"""
from fontTools.pens.basePen import BasePen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import removeOverlaps
from fontTools.varLib import instancer

# --- the fixed alphabet ------------------------------------------------------

LETTERS = "abcdefghijklmnopqrstuvwxyz"
VERBS = "MLQZ"
N_BUCKETS = 96
COORD_BASE = 0x2800  # Braille Patterns block: 96 contiguous printable chars
COORDS = "".join(chr(COORD_BASE + b) for b in range(N_BUCKETS))
BOUNDARY = "\n"
ALPHABET = LETTERS + VERBS + COORDS + BOUNDARY  # 127 chars, fixed order

EM = 1024
GRID = 16
COORD_MIN = -512  # bucket 0 -> -512; bucket 95 -> +1008


def stoi_itos():
    """The shared tokenizer contract (ADR-0012) for every glyph dataset."""
    stoi = {ch: i for i, ch in enumerate(ALPHABET)}
    itos = {i: ch for i, ch in enumerate(ALPHABET)}
    return stoi, itos


def bucket(v):
    """Em units -> grid bucket, clamped. Returns (bucket, clipped?)."""
    b = round((v - COORD_MIN) / GRID)
    if b < 0:
        return 0, True
    if b >= N_BUCKETS:
        return N_BUCKETS - 1, True
    return b, False


def unbucket(ch):
    return COORD_MIN + GRID * (ord(ch) - COORD_BASE)


# --- font -> segments --------------------------------------------------------

class _SegmentPen(BasePen):
    """Records M/L/Q segments in em-normalized coordinates.

    Cubics are converted upstream by Cu2QuPen; multi-off-curve TrueType
    qCurveTo segments are expanded here via implied on-curve midpoints, so
    every recorded Q has exactly one control point.
    """

    def __init__(self, glyphset, scale):
        super().__init__(glyphset)
        self.scale = scale
        self.contours = []  # list of [(verb, pts...), ...]
        self._cur = None

    def _pt(self, p):
        return (p[0] * self.scale, p[1] * self.scale)

    def _moveTo(self, p):
        self._cur = [("M", self._pt(p))]

    def _lineTo(self, p):
        self._cur.append(("L", self._pt(p)))

    def _qCurveToOne(self, c, p):
        self._cur.append(("Q", self._pt(c), self._pt(p)))

    def _curveToOne(self, c1, c2, p):
        raise ValueError("cubic reached the segment pen; wrap with Cu2QuPen")

    def _closePath(self):
        if self._cur:
            self.contours.append(self._cur)
        self._cur = None

    def _endPath(self):
        # open contours don't occur in binary fonts; drop defensively
        self._cur = None


def extract_glyph(font, glyphset, letter):
    """One letter from an open TTFont -> (advance_units, contours) in em-1024
    coordinates, or None if the glyph is missing or empty."""
    cmap = font.getBestCmap()
    gname = cmap.get(ord(letter))
    if gname is None:
        return None
    scale = EM / font["head"].unitsPerEm
    pen = _SegmentPen(glyphset, scale)
    glyphset[gname].draw(Cu2QuPen(pen, max_err=font["head"].unitsPerEm / 1000))
    if not pen.contours:
        return None
    adv = glyphset[gname].width * scale
    return adv, pen.contours


# --- quantize + canonicalize -------------------------------------------------

def _quantize(contours):
    """Contours -> list of point rings: [(on_pt, ctrl_or_None), ...] per
    contour, in bucket space. Each edge runs from its point to the next
    ring entry's point, optionally via next entry's control. Degenerate
    zero-length edges collapse. Returns (rings, n_clipped)."""
    n_clipped = 0

    def q(p):
        nonlocal n_clipped
        bx, cx = bucket(p[0])
        by, cy = bucket(p[1])
        n_clipped += cx + cy
        return (bx, by)

    rings = []
    for contour in contours:
        ring = []  # (point, control that led INTO this point)
        for seg in contour:
            if seg[0] == "M":
                ring.append((q(seg[1]), None))
            elif seg[0] == "L":
                ring.append((q(seg[1]), None))
            else:  # Q
                ring.append((q(seg[2]), q(seg[1])))
        # drop the closing duplicate TrueType sometimes leaves (last == first)
        if len(ring) > 1 and ring[-1][0] == ring[0][0] and ring[-1][1] is None:
            ring.pop()
        # collapse zero-length line edges
        cleaned = []
        for pt, ctrl in ring:
            if cleaned and ctrl is None and cleaned[-1][0] == pt:
                continue
            cleaned.append((pt, ctrl))
        if len(cleaned) >= 2:
            rings.append(cleaned)
    return rings, n_clipped


def _signed_area(ring):
    pts = [p for p, _ in ring]
    area = 0
    for i, (x0, y0) in enumerate(pts):
        x1, y1 = pts[(i + 1) % len(pts)]
        area += x0 * y1 - x1 * y0
    return area / 2


def _canonicalize(rings):
    canon = []
    for ring in rings:
        # clockwise everywhere; even-odd fill makes direction meaningless,
        # so normalizing it removes a spurious degree of freedom
        if _signed_area(ring) > 0:
            pts = [p for p, _ in ring]
            ctrls = [c for _, c in ring]
            # edge i runs pts[i] -> pts[i+1] via ctrls[i+1]; reversed, edge
            # runs pts[i+1] -> pts[i] via the same control
            n = len(ring)
            ring = [(pts[i % n], ctrls[(i + 1) % n]) for i in range(n, 0, -1)]
        # start at the lowest-then-leftmost on-curve point
        start = min(range(len(ring)), key=lambda i: (ring[i][0][1], ring[i][0][0]))
        ring = ring[start:] + ring[:start]
        canon.append(ring)
    canon.sort(key=lambda r: (-abs(_signed_area(r)), min(p[1] for p, _ in r), min(p[0] for p, _ in r)))
    return canon


# --- serialize / parse -------------------------------------------------------

def _c(b):
    return chr(COORD_BASE + b)


def encode_glyph(letter, adv, contours):
    """(letter, advance in em units, raw contours) -> one line (no newline).
    Returns (line, n_clipped)."""
    rings, n_clipped = _quantize(contours)
    if not rings:
        return None, n_clipped
    adv_b, adv_clip = bucket(adv)
    n_clipped += adv_clip
    out = [letter, _c(adv_b)]
    for ring in _canonicalize(rings):
        first = ring[0][0]
        out.append("M")
        out.append(_c(first[0]) + _c(first[1]))
        for i in range(1, len(ring) + 1):
            pt, ctrl = ring[i % len(ring)]
            if i == len(ring) and ctrl is None:
                break  # Z closes back to first with a straight edge
            if ctrl is None:
                out.append("L" + _c(pt[0]) + _c(pt[1]))
            else:
                out.append("Q" + _c(ctrl[0]) + _c(ctrl[1]) + _c(pt[0]) + _c(pt[1]))
        out.append("Z")
    return "".join(out), n_clipped


class GlyphSyntaxError(ValueError):
    pass


def decode_glyph(line):
    """Strict parse of one line -> dict(letter, adv, contours) where contours
    are [(verb, (x,y)...), ...] in em units. Raises GlyphSyntaxError -- this
    is the grammar validity check for model output too."""
    def is_coord(ch):
        return COORD_BASE <= ord(ch) < COORD_BASE + N_BUCKETS

    if len(line) < 2 or line[0] not in LETTERS or not is_coord(line[1]):
        raise GlyphSyntaxError("bad header (letter + advance expected)")
    letter, adv = line[0], unbucket(line[1])
    i, contours, cur = 2, [], None

    def take_pt(i):
        if i + 1 >= len(line) or not (is_coord(line[i]) and is_coord(line[i + 1])):
            raise GlyphSyntaxError(f"coordinate pair expected at {i}")
        return (unbucket(line[i]), unbucket(line[i + 1])), i + 2

    while i < len(line):
        v = line[i]
        i += 1
        if v == "M":
            if cur is not None:
                raise GlyphSyntaxError("M inside an open contour")
            p, i = take_pt(i)
            cur = [("M", p)]
        elif v == "L":
            if cur is None:
                raise GlyphSyntaxError("L outside a contour")
            p, i = take_pt(i)
            cur.append(("L", p))
        elif v == "Q":
            if cur is None:
                raise GlyphSyntaxError("Q outside a contour")
            c, i = take_pt(i)
            p, i = take_pt(i)
            cur.append(("Q", c, p))
        elif v == "Z":
            if cur is None or len(cur) < 2:
                raise GlyphSyntaxError("Z on an empty contour")
            contours.append(cur)
            cur = None
        else:
            raise GlyphSyntaxError(f"unexpected char {v!r} at {i - 1}")
    if cur is not None:
        raise GlyphSyntaxError("unclosed contour at end of line")
    if not contours:
        raise GlyphSyntaxError("no contours")
    return {"letter": letter, "adv": adv, "contours": contours}


def glyph_to_svg_path(decoded):
    """Decoded glyph -> SVG path data in em coordinates (y-up; the renderer
    applies the flip). Every contour closes with Z; fill-rule must be evenodd."""
    d = []
    for contour in decoded["contours"]:
        for seg in contour:
            if seg[0] == "M":
                d.append(f"M{seg[1][0]} {seg[1][1]}")
            elif seg[0] == "L":
                d.append(f"L{seg[1][0]} {seg[1][1]}")
            else:
                d.append(f"Q{seg[1][0]} {seg[1][1]} {seg[2][0]} {seg[2][1]}")
        d.append("Z")
    return "".join(d)


def _prep(font):
    """Overlaps are removed (skia-pathops) for the a-z glyphs before anything
    is extracted: found fonts -- variable fonts especially -- draw glyphs as
    overlapping contours (stem over bowl), and under the codec's even-odd
    fill every overlap region would render as a hole. Post-removal, contours
    are disjoint and even-odd is correct for any counter nesting."""
    cmap = font.getBestCmap()
    names = {cmap[ord(ch)] for ch in LETTERS if ord(ch) in cmap}
    if names:
        removeOverlaps(font, glyphNames=names, removeHinting=True)
    return font, font.getGlyphSet()


def open_font(path):
    """TTFont + glyphset for the file's default instance (a variable font's
    glyf table IS its default instance). Used by the round-trip sheet."""
    return _prep(TTFont(path, fontNumber=0))


def font_instances(path):
    """Yield (label, font, glyphset) for every sample a file contributes.

    A static font yields once. A variable font with a wght axis yields one
    instance per distinct named-instance weight (the designer-endorsed set
    from fvar), all other axes pinned at their defaults -- real drawn
    variation, not synthetic augmentation. Decided 2026-07-13 to lift
    per-letter corpus depth out of memorization territory: VF-only families
    otherwise contribute a single default instance each."""
    font = TTFont(path, fontNumber=0)
    if "fvar" not in font:
        yield "", *_prep(font)
        return
    axes = {a.axisTag: a for a in font["fvar"].axes}
    if "wght" not in axes:
        yield "", *_prep(font)
        return
    wghts = sorted({round(inst.coordinates.get("wght", axes["wght"].defaultValue))
                    for inst in font["fvar"].instances})
    if not wghts:
        wghts = [round(axes["wght"].defaultValue)]
    for w in wghts:
        inst = instancer.instantiateVariableFont(font, {"wght": w}, inplace=False, updateFontNames=False)
        yield f"@wght{w}", *_prep(inst)
