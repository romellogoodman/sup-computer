"""
encode_corpus.py -- run the codec over every font in the manifest.

Writes data/corpus/<letter>.txt (gitignored), one glyph per line, each line
tagged with its source so prepare.py can split by family:

    <family_dir>\\t<filename>\\t<encoded line>

The tab-separated prefix never enters a dataset -- prepare.py strips it.
Also writes data/corpus/encode-stats.json: per-letter counts, skip and clip
tallies, sequence-length percentiles.

Run from the repo root:
    uv run python projects/glyph/data/encode_corpus.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codec  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.join(HERE, "corpus")


def main():
    with open(os.path.join(HERE, "manifest.json")) as f:
        manifest = json.load(f)

    os.makedirs(CORPUS_DIR, exist_ok=True)
    lines = {ch: [] for ch in codec.LETTERS}
    stats = {
        "fonts_ok": 0, "fonts_failed": 0,
        "glyphs": 0, "glyphs_missing_or_empty": 0, "glyphs_failed": 0,
        "points_clipped_lines": 0, "failures": [],
    }
    lengths = []

    for fam in manifest["families"]:
        for file in fam["files"]:
            if not file.get("sha256"):
                continue
            path = os.path.join(HERE, "gfonts", fam["dir"], file["filename"])
            try:
                font, glyphset = codec.open_font(path)
            except Exception as e:  # unparseable font: log, move on
                stats["fonts_failed"] += 1
                stats["failures"].append(f"{fam['dir']}/{file['filename']}: open: {e}")
                continue
            stats["fonts_ok"] += 1
            for letter in codec.LETTERS:
                try:
                    got = codec.extract_glyph(font, glyphset, letter)
                    if got is None:
                        stats["glyphs_missing_or_empty"] += 1
                        continue
                    adv, contours = got
                    line, n_clipped = codec.encode_glyph(letter, adv, contours)
                    if line is None:
                        stats["glyphs_missing_or_empty"] += 1
                        continue
                    codec.decode_glyph(line)  # every emitted line must re-parse
                except Exception as e:
                    stats["glyphs_failed"] += 1
                    stats["failures"].append(f"{fam['dir']}/{file['filename']} {letter!r}: {e}")
                    continue
                if n_clipped:
                    stats["points_clipped_lines"] += 1
                stats["glyphs"] += 1
                lengths.append(len(line))
                lines[letter].append(f"{fam['dir']}\t{file['filename']}\t{line}")
            font.close()

    for letter, ls in lines.items():
        with open(os.path.join(CORPUS_DIR, f"{letter}.txt"), "w") as f:
            f.write("\n".join(ls) + "\n")

    lengths.sort()
    pct = lambda p: lengths[int(p * (len(lengths) - 1))] if lengths else 0  # noqa: E731
    stats["per_letter"] = {ch: len(ls) for ch, ls in lines.items()}
    stats["line_length"] = {"p50": pct(.5), "p90": pct(.9), "p99": pct(.99), "max": lengths[-1] if lengths else 0}
    stats["failures"] = stats["failures"][:200]
    with open(os.path.join(CORPUS_DIR, "encode-stats.json"), "w") as f:
        json.dump(stats, f, indent=1)

    print(f"fonts: {stats['fonts_ok']} ok, {stats['fonts_failed']} failed to open")
    print(f"glyphs: {stats['glyphs']:,} encoded; {stats['glyphs_missing_or_empty']:,} missing/empty; "
          f"{stats['glyphs_failed']:,} failed; {stats['points_clipped_lines']:,} lines had clipped points")
    print(f"line length p50/p90/p99/max: {stats['line_length']['p50']}/{stats['line_length']['p90']}"
          f"/{stats['line_length']['p99']}/{stats['line_length']['max']}")
    per = stats["per_letter"]
    print(f"per letter: min {min(per.values()):,} ({min(per, key=per.get)!r})  "
          f"max {max(per.values()):,} ({max(per, key=per.get)!r})")


if __name__ == "__main__":
    main()
