"""
roundtrip_sheet.py -- the pre-training legibility gate (look at it).

Renders 'handgloves' (ascenders, descenders, rounds, the hard g) for a
deterministic sample of manifest families: the original outlines in gray,
the encode->decode round trip in black directly beneath. If the 16-unit
grid mangles legibility here, the codec changes before anything trains.

Writes research/roundtrip-sheet.html (committed evidence).

Run from the repo root:
    uv run python projects/glyph/data/roundtrip_sheet.py
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codec  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "research", "roundtrip-sheet.html")
WORD = "handgloves"
N_FAMILIES = 20


def contours_to_path(contours):
    """Full-precision segments (from _SegmentPen) -> SVG path data, y-up."""
    d = []
    for contour in contours:
        for seg in contour:
            if seg[0] == "M":
                d.append(f"M{seg[1][0]:.1f} {seg[1][1]:.1f}")
            elif seg[0] == "L":
                d.append(f"L{seg[1][0]:.1f} {seg[1][1]:.1f}")
            else:
                d.append(f"Q{seg[1][0]:.1f} {seg[1][1]:.1f} {seg[2][0]:.1f} {seg[2][1]:.1f}")
        d.append("Z")
    return "".join(d)


def word_svg(glyphs, color):
    """[(adv, path_d)] -> one svg of the word set on its real advances."""
    parts, x = [], 0
    for adv, d in glyphs:
        parts.append(f'<path transform="translate({x:.0f},0)" d="{d}"/>')
        x += adv
    return (f'<svg viewBox="0 -1100 {x:.0f} 1700" height="52" '
            f'style="display:block" fill="{color}" fill-rule="evenodd">'
            f'<g transform="scale(1,-1)">{"".join(parts)}</g></svg>')


def main():
    with open(os.path.join(HERE, "manifest.json")) as f:
        manifest = json.load(f)

    fams = sorted(manifest["families"], key=lambda f: hashlib.md5(f["name"].encode()).hexdigest())
    rows, used = [], 0
    for fam in fams:
        if used >= N_FAMILIES:
            break
        file = next((f for f in fam["files"] if f.get("sha256")), None)
        if file is None:
            continue
        font, glyphset = codec.open_font(os.path.join(HERE, "gfonts", fam["dir"], file["filename"]))
        orig, rt = [], []
        try:
            for ch in WORD:
                got = codec.extract_glyph(font, glyphset, ch)
                if got is None:
                    raise KeyError(ch)
                adv, contours = got
                line, _ = codec.encode_glyph(ch, adv, contours)
                if line is None:
                    raise KeyError(ch)
                decoded = codec.decode_glyph(line)
                orig.append((adv, contours_to_path(contours)))
                rt.append((decoded["adv"], codec.glyph_to_svg_path(decoded)))
        except KeyError:
            continue  # family lacks a letter of the word; sample the next one
        finally:
            font.close()
        rows.append(
            f'<div class="row"><div class="label">{fam["name"]} '
            f'<span class="file">{file["filename"]}</span></div>'
            f'{word_svg(orig, "#999")}{word_svg(rt, "#111")}</div>'
        )
        used += 1

    html = f"""<!doctype html><meta charset="utf-8">
<title>glyph codec round-trip sheet</title>
<style>
  body {{ font: 13px/1.4 system-ui; margin: 2rem auto; max-width: 720px; }}
  .row {{ margin-bottom: 1.6rem; }}
  .label {{ color: #444; margin-bottom: .3rem; }}
  .file {{ color: #999; }}
  svg {{ margin-bottom: 2px; }}
</style>
<h1>Round-trip: original (gray) vs codec (black)</h1>
<p>'{WORD}', {used} manifest families sampled deterministically (md5 of the
family name). Em normalized to 1024, coordinates on a 16-unit grid,
cubics&rarr;quadratics, contours canonicalized. Regenerate:
<code>uv run python projects/glyph/data/roundtrip_sheet.py</code></p>
{"".join(rows)}"""
    with open(OUT, "w") as f:
        f.write(html)
    print(f"wrote {used} families -> {os.path.normpath(OUT)}")


if __name__ == "__main__":
    main()
