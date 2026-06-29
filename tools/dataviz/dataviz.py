"""sup computer dataviz pipeline — chart renderer.

Pure-stdlib. Produces self-contained HTML files with inline SVG, styled to match
the studio website's refined "Prof. Dr." document look (system serif + monospace,
no webfont, no corner radius, one green accent — see designsystem/tokens.py and
docs/adr/0018). No external libraries, no network at view time.

Public API:
    bar(spec, mode="light")   -> html string   (vertical bars, supports negatives)
    line(spec, mode="light")  -> html string   (single/multi-series line)
    write(html, path)

A `spec` is a dict:
    {
      "title": str,
      "subtitle": str | None,
      "caption": str | None,
      "yTitle": str, "xTitle": str,
      # bar:
      "categories": [str, ...],
      "values": [float, ...],
      "colors": [hueName, ...] | None,   # per-bar hue from tokens; default "blue"
      "valueFmt": "{:.3f}" (format string for labels/tooltips),
      "lowerIsBetter": bool,             # cosmetic note in <desc>
      # line:
      "x": [num|str, ...],
      "series": [{"name": str, "y": [float,...], "hue": hueName}],
    }
"""
import math
import os
from html import escape

from designsystem.tokens import (
    FONT_SERIF, FONT_MONO, TYPE, SPACE, RADIUS, CAP_H, HUE_ORDER, theme,
)

_HERE = os.path.dirname(os.path.abspath(__file__))
VIEW_W = 960  # desktop viewBox width


# --- helpers ----------------------------------------------------------------
def _role_font(role: str) -> str:
    return FONT_MONO if TYPE[role].get("font") == "mono" else FONT_SERIF


def _text_w(s: str, size: float) -> float:
    """Rough advance-width estimate (mono ~0.6em, serif ~0.52em; 0.57 splits it)."""
    return len(str(s)) * 0.57 * size


def _nice_num(x: float, round_down: bool) -> float:
    if x <= 0:
        return 1.0
    exp = math.floor(math.log10(x))
    f = x / (10 ** exp)
    if round_down:
        nf = 1 if f < 1.5 else (2 if f < 3 else (5 if f < 7 else 10))
    else:
        nf = 1 if f <= 1 else (2 if f <= 2 else (5 if f <= 5 else 10))
    return nf * (10 ** exp)


def _nice_axis(dmin: float, dmax: float, target=5):
    """Return (axisMin, axisMax, [ticks]). Includes 0 in range for bars."""
    if dmin == dmax:
        dmax = dmin + 1
    rng = _nice_num(dmax - dmin, False)
    step = _nice_num(rng / (target - 1), True)
    axmin = math.floor(dmin / step) * step
    axmax = math.ceil(dmax / step) * step
    ticks, t = [], axmin
    # guard against float drift
    while t <= axmax + step * 0.5:
        ticks.append(round(t, 10))
        t += step
    return axmin, axmax, ticks


def _fmt_tick(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return ("%g" % v)


def _txt(x, y, s, role, color, anchor="start", baseline="auto", t=None):
    sty = TYPE[role]
    tracking = f' letter-spacing="{sty["tracking"]}"' if sty["tracking"] else ""
    italic = ' font-style="italic"' if sty.get("italic") else ""
    extra = f' data-tooltip="{escape(str(t))}"' if t else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family=\'{_role_font(role)}\' '
        f'font-size="{sty["size"]}" font-weight="{sty["weight"]}"{tracking}{italic} '
        f'fill="{color}" text-anchor="{anchor}" dominant-baseline="{baseline}"{extra}>'
        f'{escape(str(s))}</text>'
    )


# --- HTML wrapper -----------------------------------------------------------
def _wrap(svg: str, title: str, tk: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: {FONT_SERIF};
  background: {tk["surface"]};
  display: flex; justify-content: center; padding: 24px;
}}
.chart {{ width: 100%; max-width: 960px; position: relative; }}
svg {{ width: 100%; height: auto; display: block; }}
svg text {{ font-family: {FONT_SERIF}; }}
.bar, .dot {{ transition: opacity .15s; cursor: pointer; }}
.bar:hover {{ opacity: .82; }}
.dot {{ transition: r .15s; }}
.dot:hover {{ r: 6; }}
.tip {{
  position: fixed; background: {tk["tooltipBg"]}; color: {tk["tooltipText"]};
  padding: 6px 9px; border-radius: 0; font-family: {FONT_MONO};
  font-size: 12px; font-weight: 400;
  pointer-events: none; opacity: 0; transition: opacity .12s; white-space: nowrap;
  z-index: 10;
}}
.tip.on {{ opacity: 1; }}
</style>
</head>
<body>
<div class="chart">{svg}</div>
<div class="tip" id="tip"></div>
<script>
const tip = document.getElementById('tip');
document.querySelectorAll('[data-tooltip]').forEach(el => {{
  el.addEventListener('mouseenter', () => {{ tip.textContent = el.dataset.tooltip; tip.classList.add('on'); }});
  el.addEventListener('mousemove', e => {{ tip.style.left = (e.clientX + 12) + 'px'; tip.style.top = (e.clientY - 32) + 'px'; }});
  el.addEventListener('mouseleave', () => tip.classList.remove('on'));
}});
</script>
</body>
</html>"""


# --- shared header layout (title / subtitle) --------------------------------
def _header(tk, title, subtitle, body_x, body_w):
    L, S = SPACE["L"], SPACE["S"]
    parts, y = [], L
    cx = body_x + body_w / 2
    y += TYPE["title"]["size"] * CAP_H
    parts.append(_txt(cx, y, title, "title", tk["primary"], "middle"))
    if subtitle:
        y += S
        y += TYPE["subtitle"]["size"] * CAP_H
        parts.append(_txt(cx, y, subtitle, "subtitle", tk["secondary"], "middle"))
    y += L  # gap to chart body
    return parts, y


def _wrap_words(text: str, max_w: float, size: float):
    """Greedy word-wrap to a pixel width. Returns list of lines."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if _text_w(trial, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _footer(tk, caption, body_x, body_w, y):
    """Caption (word-wrapped) with a separator rule. Returns (svg_parts, new_y)."""
    if not caption:
        return [], y + SPACE["L"]
    L, M = SPACE["L"], SPACE["M"]
    size = TYPE["caption"]["size"]
    line_h = TYPE["caption"]["line"]
    parts = []
    y += L
    parts.append(f'<line x1="{body_x:.1f}" y1="{y:.1f}" x2="{body_x+body_w:.1f}" '
                 f'y2="{y:.1f}" stroke="{tk["grid"]}" stroke-width="1"/>')
    y += M
    for i, ln in enumerate(_wrap_words(caption, body_w, size)):
        ly = y + size * CAP_H + i * line_h
        parts.append(_txt(body_x, ly, ln, "caption", tk["muted"], "start"))
    # advance past all lines
    n_lines = len(_wrap_words(caption, body_w, size))
    y += size * CAP_H + (n_lines - 1) * line_h
    y += L
    return parts, y


# --- vertical bar chart (supports negative values) --------------------------
def bar(spec: dict, mode: str = "light") -> str:
    tk = theme(mode)
    L, M, S, XS = SPACE["L"], SPACE["M"], SPACE["S"], SPACE["XS"]
    cats = spec["categories"]
    vals = spec["values"]
    n = len(cats)
    fmt = spec.get("valueFmt", "{:.3f}")
    colors = spec.get("colors") or ["blue"] * n

    # value axis (include zero)
    dmin = min(0.0, min(vals))
    dmax = max(0.0, max(vals))
    axmin, axmax, ticks = _nice_axis(dmin, dmax)

    # left zone: y-title + widest tick label
    tickw = max(_text_w(_fmt_tick(t), TYPE["tick"]["size"]) for t in ticks)
    left = M + TYPE["axisTitle"]["size"] + S + tickw + S
    right = left
    body_x = left
    body_w = VIEW_W - left - right
    body_h = round(body_w * 9 / 16)

    head, y = _header(tk, spec["title"], spec.get("subtitle"), body_x, body_w)
    body_y = y
    y += body_h

    def v2y(v):
        return body_y + body_h - (v - axmin) / (axmax - axmin) * body_h

    zeroY = v2y(0)
    svg = list(head)

    # gridlines + tick labels
    for t in ticks:
        ty = v2y(t)
        svg.append(f'<line x1="{body_x:.1f}" y1="{ty:.1f}" x2="{body_x+body_w:.1f}" '
                   f'y2="{ty:.1f}" stroke="{tk["grid"]}" stroke-width="1"/>')
        svg.append(_txt(body_x - S, ty, _fmt_tick(t), "tick", tk["secondary"],
                        "end", "middle"))

    # bars
    avail = body_w - 2 * L
    gut = (n - 1) * M
    bw = (avail - gut) / n
    label_rotate = max(_text_w(c, TYPE["tick"]["size"]) for c in cats) > (bw - S)

    for i, (c, v) in enumerate(zip(cats, vals)):
        bx = body_x + L + i * (bw + M)
        col = tk[colors[i]]
        vy = v2y(v)
        top = min(vy, zeroY)
        h = abs(vy - zeroY)
        tip = f"{c}: {fmt.format(v)}"
        if h >= 8:  # rounded top corners (or bottom for negative)
            r = RADIUS
            if v >= 0:
                d = (f"M {bx:.1f} {top+h:.1f} V {top+r:.1f} Q {bx:.1f} {top:.1f} "
                     f"{bx+r:.1f} {top:.1f} H {bx+bw-r:.1f} Q {bx+bw:.1f} {top:.1f} "
                     f"{bx+bw:.1f} {top+r:.1f} V {top+h:.1f} Z")
            else:
                btm = top + h
                d = (f"M {bx:.1f} {top:.1f} H {bx+bw:.1f} V {btm-r:.1f} "
                     f"Q {bx+bw:.1f} {btm:.1f} {bx+bw-r:.1f} {btm:.1f} "
                     f"H {bx+r:.1f} Q {bx:.1f} {btm:.1f} {bx:.1f} {btm-r:.1f} Z")
            svg.append(f'<path d="{d}" fill="{col}" class="bar" data-tooltip="{escape(tip)}"/>')
        else:
            svg.append(f'<rect x="{bx:.1f}" y="{top:.1f}" width="{bw:.1f}" '
                       f'height="{max(h,1):.1f}" fill="{col}" class="bar" '
                       f'data-tooltip="{escape(tip)}"/>')
        # data label
        if v >= 0:
            ly = top - XS / 2
            svg.append(_txt(bx + bw / 2, ly, fmt.format(v), "dataLabel", tk["primary"],
                            "middle", "auto"))
        else:
            ly = top + h + XS + TYPE["dataLabel"]["size"] * CAP_H
            svg.append(_txt(bx + bw / 2, ly, fmt.format(v), "dataLabel", tk["primary"],
                            "middle", "auto"))
        # category label
        if label_rotate:
            ay = body_y + body_h + S
            svg.append(f'<g transform="translate({bx+bw/2:.1f},{ay:.1f}) rotate(-45)">'
                       + _txt(0, 0, c, "tick", tk["secondary"], "end", "hanging") + '</g>')
        else:
            ly = body_y + body_h + S + TYPE["tick"]["size"] * CAP_H
            svg.append(_txt(bx + bw / 2, ly, c, "tick", tk["secondary"], "middle", "auto"))

    # x-label zone height
    if label_rotate:
        drop = (max(_text_w(c, TYPE["tick"]["size"]) for c in cats) * 0.707
                + TYPE["tick"]["size"] * CAP_H * 0.707)
        y += S + drop
    else:
        y += S + TYPE["tick"]["size"] * CAP_H

    # axis origin line (zero baseline), on top of bars
    svg.append(f'<line x1="{body_x:.1f}" y1="{zeroY:.1f}" x2="{body_x+body_w:.1f}" '
               f'y2="{zeroY:.1f}" stroke="{tk["primary"]}" stroke-width="1"/>')

    # x-axis title
    y += M
    y += TYPE["axisTitle"]["size"] * CAP_H
    svg.append(_txt(body_x + body_w / 2, y, spec["xTitle"], "axisTitle", tk["primary"], "middle"))

    # y-axis title (rotated)
    yt_x = M + TYPE["axisTitle"]["size"] / 2
    yt_y = body_y + body_h / 2
    sty = TYPE["axisTitle"]
    svg.append(f'<text transform="translate({yt_x:.1f},{yt_y:.1f}) rotate(-90)" '
               f'text-anchor="middle" dominant-baseline="central" '
               f'font-family=\'{FONT_MONO}\' font-size="{sty["size"]}" '
               f'font-weight="{sty["weight"]}" letter-spacing="{sty["tracking"]}" '
               f'fill="{tk["primary"]}">{escape(spec["yTitle"])}</text>')

    # caption
    foot, y = _footer(tk, spec.get("caption"), body_x, body_w, y)
    svg += foot

    desc = (f'{spec["title"]}. Bar chart of {spec["yTitle"]} across {n} categories'
            + (', lower is better' if spec.get("lowerIsBetter") else '') + '.')
    inner = "".join(svg)
    out = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W} {y:.0f}" '
           f'role="img" aria-label="{escape(desc)}">'
           f'<rect width="{VIEW_W}" height="{y:.0f}" fill="{tk["surface"]}"/>'
           f'{inner}</svg>')
    return _wrap(out, spec["title"], tk)


# --- line chart -------------------------------------------------------------
def line(spec: dict, mode: str = "light") -> str:
    tk = theme(mode)
    L, M, S, XS = SPACE["L"], SPACE["M"], SPACE["S"], SPACE["XS"]
    xs = spec["x"]
    series = spec["series"]
    fmt = spec.get("valueFmt", "{:.2f}")
    npts = len(xs)

    all_y = [v for s in series for v in s["y"]]
    dmin = min(0.0, min(all_y)) if spec.get("zeroBase", True) else min(all_y)
    dmax = max(all_y)
    axmin, axmax, ticks = _nice_axis(dmin, dmax)

    tickw = max(_text_w(_fmt_tick(t), TYPE["tick"]["size"]) for t in ticks)
    left = M + TYPE["axisTitle"]["size"] + S + tickw + S
    right = left
    body_x = left
    body_w = VIEW_W - left - right
    body_h = round(body_w * 9 / 16)

    head, y = _header(tk, spec["title"], spec.get("subtitle"), body_x, body_w)
    body_y = y
    y += body_h

    def v2y(v):
        return body_y + body_h - (v - axmin) / (axmax - axmin) * body_h

    inset = L
    def i2x(i):
        return body_x + inset + i * (body_w - 2 * inset) / max(npts - 1, 1)

    svg = list(head)

    # gridlines + y tick labels
    for t in ticks:
        ty = v2y(t)
        svg.append(f'<line x1="{body_x:.1f}" y1="{ty:.1f}" x2="{body_x+body_w:.1f}" '
                   f'y2="{ty:.1f}" stroke="{tk["grid"]}" stroke-width="1"/>')
        svg.append(_txt(body_x - S, ty, _fmt_tick(t), "tick", tk["secondary"], "end", "middle"))

    # x tick labels (under each point)
    lx_y = body_y + body_h + S + TYPE["tick"]["size"] * CAP_H
    for i, xv in enumerate(xs):
        svg.append(_txt(i2x(i), lx_y, xv, "tick", tk["secondary"], "middle", "auto"))

    # series: polyline + dots
    for s in series:
        col = tk[s.get("hue", "blue")]
        pts = " ".join(f"{i2x(i):.1f},{v2y(v):.1f}" for i, v in enumerate(s["y"]))
        svg.append(f'<polyline points="{pts}" fill="none" stroke="{col}" '
                   f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        for i, v in enumerate(s["y"]):
            tip = f'{s["name"]} — {xs[i]}: {fmt.format(v)}'
            svg.append(f'<circle cx="{i2x(i):.1f}" cy="{v2y(v):.1f}" r="4" '
                       f'fill="{col}" stroke="{tk["surface"]}" stroke-width="1" '
                       f'class="dot" data-tooltip="{escape(tip)}"/>')

    y += S + TYPE["tick"]["size"] * CAP_H

    # axis origin line
    svg.append(f'<line x1="{body_x:.1f}" y1="{body_y+body_h:.1f}" '
               f'x2="{body_x+body_w:.1f}" y2="{body_y+body_h:.1f}" '
               f'stroke="{tk["primary"]}" stroke-width="1"/>')

    # x-axis title
    y += M
    y += TYPE["axisTitle"]["size"] * CAP_H
    svg.append(_txt(body_x + body_w / 2, y, spec["xTitle"], "axisTitle", tk["primary"], "middle"))

    # y-axis title
    yt_x = M + TYPE["axisTitle"]["size"] / 2
    yt_y = body_y + body_h / 2
    sty = TYPE["axisTitle"]
    svg.append(f'<text transform="translate({yt_x:.1f},{yt_y:.1f}) rotate(-90)" '
               f'text-anchor="middle" dominant-baseline="central" '
               f'font-family=\'{FONT_MONO}\' font-size="{sty["size"]}" '
               f'font-weight="{sty["weight"]}" letter-spacing="{sty["tracking"]}" '
               f'fill="{tk["primary"]}">{escape(spec["yTitle"])}</text>')

    foot, y = _footer(tk, spec.get("caption"), body_x, body_w, y)
    svg += foot

    desc = f'{spec["title"]}. Line chart of {spec["yTitle"]} over {spec["xTitle"]}.'
    inner = "".join(svg)
    out = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW_W} {y:.0f}" '
           f'role="img" aria-label="{escape(desc)}">'
           f'<rect width="{VIEW_W}" height="{y:.0f}" fill="{tk["surface"]}"/>'
           f'{inner}</svg>')
    return _wrap(out, spec["title"], tk)


def write(html: str, path: str):
    with open(path, "w") as f:
        f.write(html)
    return path
