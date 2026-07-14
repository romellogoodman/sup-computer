"""
specimen.py -- render encoded glyph lines into report-ready PNG pairs.

Specimens are artifacts, not charts (charts go through tools/dataviz); this
renders sampled or corpus glyphs into a labeled grid and screenshots it via
headless Chrome to research-docs/reports/assets/<name>.{light,dark}.png,
transparent background, 2x scale -- the same <picture> embed convention the
reports already use.

Row spec (repeatable): --row "label|path|letter|n|mode"
  path    file of encoded lines: run-dir samples-*.txt (raw model output,
          "!" = unterminated) or data/corpus/<letter>.txt (provenance-
          prefixed; the tab prefix is stripped automatically)
  letter  keep lines whose glyph is this letter ("." = any)
  n       how many cells
  mode    "valid" = parseable glyphs only; "all" = keep failures too,
          rendered as an x-slot (for failure galleries)

Example:
  uv run python projects/glyph/specimen.py --out exp11-case-a \\
      --row "specialist a, temp 1.0|projects/glyph/runs/a-r1/samples-a-t1.0.txt|a|13|valid"
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
import codec  # noqa: E402

ASSETS = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "research-docs", "reports", "assets"))
CELL_W, PAD, LABEL_H = 92, 10, 26
CELL_H = round(CELL_W * 1700 / 1152)
CHROME = os.environ.get("DATAVIZ_CHROME",
                        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def load_rows(specs):
    rows = []
    for spec in specs:
        label, path, letter, n, mode = spec.split("|")
        cells, n = [], int(n)
        with open(path) as f:
            for raw in f:
                line = raw.rstrip("\n")
                if "\t" in line:
                    line = line.split("\t")[-1]
                if not line:
                    continue
                try:
                    g = codec.decode_glyph(line)
                    ok = letter == "." or g["letter"] == letter
                    cell = codec.glyph_to_svg_path(g) if ok else None
                except codec.GlyphSyntaxError:
                    ok, cell = mode == "all" and (letter == "." or line[:1] == letter), None
                if not ok:
                    continue
                if cell is None and mode != "all":
                    continue
                cells.append(cell)
                if len(cells) == n:
                    break
        rows.append((label, cells))
    return rows


def render_svg(rows, fg):
    ncols = max(len(c) for _, c in rows)
    width = PAD * 2 + ncols * (CELL_W + PAD)
    height = PAD + sum(LABEL_H + CELL_H + PAD for _ in rows)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">']
    y = PAD
    for label, cells in rows:
        parts.append(f'<text x="{PAD}" y="{y + 16}" fill="{fg}" opacity="0.65" '
                     f'font-family="system-ui" font-size="13">{label}</text>')
        y += LABEL_H
        for i, d in enumerate(cells):
            x = PAD + i * (CELL_W + PAD)
            if d is None:  # failure slot
                parts.append(f'<text x="{x + CELL_W / 2}" y="{y + CELL_H / 2}" fill="{fg}" '
                             f'opacity="0.3" font-family="system-ui" font-size="20" '
                             f'text-anchor="middle">&#215;</text>')
                continue
            sx = CELL_W / 1152
            parts.append(f'<g transform="translate({x + 64 * sx},{y + CELL_H * (600 / 1700)}) '
                         f'scale({sx},-{sx})"><path d="{d}" fill="{fg}" fill-rule="evenodd"/></g>')
        y += CELL_H + PAD
    parts.append("</svg>")
    return "".join(parts), width, height


def screenshot(svg, width, height, out_png):
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as f:
        f.write(svg)
        tmp = f.name
    try:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                        f"--screenshot={out_png}", f"--window-size={width},{height}",
                        "--default-background-color=00000000",
                        "--force-device-scale-factor=2", "--hide-scrollbars",
                        f"file://{tmp}"], check=True, capture_output=True)
    finally:
        os.unlink(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="asset base name, e.g. exp11-case-specimen")
    ap.add_argument("--row", action="append", required=True,
                    help="label|path|letter|n|mode (mode: valid|all)")
    args = ap.parse_args()
    if not shutil.which(CHROME) and not os.path.exists(CHROME):
        sys.exit(f"Chrome not found at {CHROME} (set DATAVIZ_CHROME)")

    rows = load_rows(args.row)
    os.makedirs(ASSETS, exist_ok=True)
    for mode, fg in (("light", "#141414"), ("dark", "#ececec")):
        svg, w, h = render_svg(rows, fg)
        out = os.path.join(ASSETS, f"{args.out}.{mode}.png")
        screenshot(svg, w, h, out)
        print(f"wrote {os.path.relpath(out)} ({w}x{h}@2x)")


if __name__ == "__main__":
    main()
