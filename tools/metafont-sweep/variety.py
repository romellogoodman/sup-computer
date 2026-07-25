"""
variety.py -- how much information is in a corpus of letterforms?

Two arms, same codec, same alphabet, same quantization:
  generative -- N independent designers, one glyph each
  parametric -- N settings of one program's parameter vector

Measures, per arm:
  1. intrinsic dimensionality   PCA components to reach 90/95/99% of variance
  2. saturation                 compressed bytes bought by the Nth added glyph
  3. span                       fraction of the generative arm's variance that
                                the parametric arm's principal subspace covers
  4. unigram BPC                corpus entropy in the codec's own alphabet

Rasterization is deliberately un-normalized: x-height and stem weight are
exactly what a parameter sweep varies, so scaling them away would erase the
thing under test. Both arms share one fixed em window.
"""
import gzip
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GLYPH_DATA = os.path.join(REPO, "projects", "glyph", "data")
sys.path.insert(0, GLYPH_DATA)
import codec  # noqa: E402

# fixed em window shared by both arms (em is 1024; letters sit well inside)
WIN_X0, WIN_X1 = -80.0, 880.0
WIN_Y0, WIN_Y1 = -260.0, 800.0
RES = 48        # raster is RES x RES
SS = 3          # supersample factor before box-averaging
QSTEPS = 8      # polyline steps per quadratic


def load_corpus(path, letter=None):
    """corpus/<letter>.txt -> [(family, source, line)]. Lines are tab-tagged."""
    out = []
    with open(path) as f:
        for raw in f:
            raw = raw.rstrip("\n")
            if not raw:
                continue
            fam, src, line = raw.split("\t")
            if letter and line[0] != letter:
                continue
            out.append((fam, src, line))
    return out


def _polygons(line):
    """decoded glyph -> list of closed polygons (numpy arrays of vertices)."""
    dec = codec.decode_glyph(line)
    polys = []
    for contour in dec["contours"]:
        pts = []
        cur = None
        for seg in contour:
            if seg[0] == "M":
                cur = np.array(seg[1], dtype=float)
                pts.append(cur)
            elif seg[0] == "L":
                cur = np.array(seg[1], dtype=float)
                pts.append(cur)
            else:  # Q: flatten
                c = np.array(seg[1], dtype=float)
                p = np.array(seg[2], dtype=float)
                t = np.linspace(0, 1, QSTEPS + 1)[1:, None]
                seg_pts = (1 - t) ** 2 * cur + 2 * (1 - t) * t * c + t**2 * p
                pts.extend(seg_pts)
                cur = p
        if len(pts) >= 3:
            polys.append(np.array(pts))
    return polys


def raster(line, res=RES, ss=SS):
    """One encoded glyph -> (res*res,) float vector, even-odd filled."""
    h = res * ss
    grid = np.zeros((h, h), dtype=np.float32)
    polys = _polygons(line)
    if not polys:
        return grid.reshape(-1)

    # edges of every contour, in pixel space
    x0s, y0s, x1s, y1s = [], [], [], []
    for poly in polys:
        px = (poly[:, 0] - WIN_X0) / (WIN_X1 - WIN_X0) * h
        py = (poly[:, 1] - WIN_Y0) / (WIN_Y1 - WIN_Y0) * h
        x0s.append(px)
        y0s.append(py)
        x1s.append(np.roll(px, -1))
        y1s.append(np.roll(py, -1))
    x0 = np.concatenate(x0s)
    y0 = np.concatenate(y0s)
    x1 = np.concatenate(x1s)
    y1 = np.concatenate(y1s)

    rows = np.arange(h) + 0.5
    dy = y1 - y0
    live = dy != 0
    x0, y0, x1, y1, dy = x0[live], y0[live], x1[live], y1[live], dy[live]
    dxdy = (x1 - x0) / dy

    for r, yc in enumerate(rows):
        hit = ((y0 <= yc) & (y1 > yc)) | ((y1 <= yc) & (y0 > yc))
        if not hit.any():
            continue
        xs = np.sort(x0[hit] + (yc - y0[hit]) * dxdy[hit])
        for a, b in zip(xs[0::2], xs[1::2]):
            lo, hi = int(np.ceil(a - 0.5)), int(np.ceil(b - 0.5))
            if hi > lo:
                grid[r, max(lo, 0):min(hi, h)] = 1.0

    # y-up -> y-down, then box-average back to res
    grid = grid[::-1]
    return grid.reshape(res, ss, res, ss).mean(axis=(1, 3)).reshape(-1)


def rasterize_all(lines, res=RES):
    X = np.zeros((len(lines), res * res), dtype=np.float32)
    for i, line in enumerate(lines):
        X[i] = raster(line, res=res)
    return X


def pca_spectrum(X):
    """-> (explained variance ratios, components, mean)."""
    mu = X.mean(axis=0)
    Xc = X - mu
    # economy SVD; components are rows of Vt
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    var = S**2
    return var / var.sum(), Vt, mu


def dims_for(ratios, targets=(0.90, 0.95, 0.99)):
    c = np.cumsum(ratios)
    return {t: int(np.searchsorted(c, t) + 1) for t in targets}


def span_fraction(X_target, Vt_basis, mu_basis, k):
    """Fraction of X_target's variance lying in the basis arm's top-k subspace.

    Centered on the basis arm's own mean, so this answers: 'if you stood at
    the parametric corpus and moved along its k strongest directions, how
    much of the generative corpus could you reach?'
    """
    Xc = X_target - mu_basis
    B = Vt_basis[:k]                       # (k, D), orthonormal rows
    proj = Xc @ B.T                        # coordinates in the subspace
    resid = Xc - proj @ B
    return 1.0 - (resid**2).sum() / (Xc**2).sum()


def saturation(lines, rng, points=24):
    """Compressed bytes of a corpus of N lines, for N along a log grid.

    Shuffled so the curve measures the corpus, not the file order.
    """
    order = rng.permutation(len(lines))
    ns = np.unique(np.geomspace(4, len(lines), points).astype(int))
    out = []
    for n in ns:
        blob = "\n".join(lines[i] for i in order[:n]).encode()
        out.append((int(n), len(gzip.compress(blob, 9))))
    return out


def unigram_bpc(lines):
    """Entropy of the corpus under a unigram model over the 127-char alphabet."""
    counts = np.zeros(len(codec.ALPHABET))
    idx = {c: i for i, c in enumerate(codec.ALPHABET)}
    total = 0
    for line in lines:
        for ch in line:
            counts[idx[ch]] += 1
            total += 1
    p = counts[counts > 0] / total
    return float(-(p * np.log2(p)).sum())
