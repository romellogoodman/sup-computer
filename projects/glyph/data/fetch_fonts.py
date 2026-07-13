"""
fetch_fonts.py -- freeze the glyph corpus pool.

Sparse, blobless clone of github.com/google/fonts in two stages:

  1. check out only ofl/*/METADATA.pb (small), parse the text-format
     protobuf by hand (no protobuf dep), and select families:
     license OFL (by directory), category SANS_SERIF, upright styles only.
  2. extend the sparse checkout to the selected families' *.ttf files
     (never the specimen images/articles -- that's most of the repo's bulk).

Output:
  data/gfonts/          the clone (gitignored)
  data/manifest.json    committed provenance: pinned upstream commit, and
                        per family: dir, name, files (filename, weight,
                        style, variable flag, sha256).

Re-running against an existing clone re-selects and rewrites the manifest;
the pinned sha records what HEAD was when the pool was frozen.

Run from the repo root:
    uv run python projects/glyph/data/fetch_fonts.py
"""
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLONE_DIR = os.path.join(HERE, "gfonts")
MANIFEST_PATH = os.path.join(HERE, "manifest.json")
UPSTREAM = "https://github.com/google/fonts.git"


def run(args, **kw):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kw)


def git(*args):
    return run(["git", "-C", CLONE_DIR, *args])


def clone_metadata_stage():
    if not os.path.isdir(os.path.join(CLONE_DIR, ".git")):
        print(f"cloning {UPSTREAM} (blobless, no checkout) ...")
        run(["git", "clone", "--depth", "1", "--filter=blob:none", "--no-checkout", UPSTREAM, CLONE_DIR])
    git("sparse-checkout", "init", "--no-cone")
    print("checking out ofl/*/METADATA.pb ...")
    git("sparse-checkout", "set", "ofl/*/METADATA.pb")
    git("checkout", "main")
    return git("rev-parse", "HEAD").stdout.strip()


def parse_metadata(path):
    """Minimal text-format protobuf reader for the fields we need."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    name = re.search(r'^name:\s*"(.*?)"', text, re.M)
    category = re.findall(r'^category:\s*"(.*?)"', text, re.M)
    fonts = []
    for block in re.findall(r"^fonts\s*\{(.*?)^\}", text, re.M | re.S):
        style = re.search(r'style:\s*"(.*?)"', block)
        weight = re.search(r"weight:\s*(\d+)", block)
        filename = re.search(r'filename:\s*"(.*?)"', block)
        if style and filename:
            fonts.append({
                "filename": filename.group(1),
                "style": style.group(1),
                "weight": int(weight.group(1)) if weight else None,
            })
    return {
        "name": name.group(1) if name else None,
        "category": category,
        "fonts": fonts,
    }


def select_families():
    ofl = os.path.join(CLONE_DIR, "ofl")
    selected, n_scanned = [], 0
    for d in sorted(os.listdir(ofl)):
        mp = os.path.join(ofl, d, "METADATA.pb")
        if not os.path.isfile(mp):
            continue
        n_scanned += 1
        meta = parse_metadata(mp)
        if "SANS_SERIF" not in meta["category"]:
            continue
        # upright only -- the italic flag flips shape class (single-story a's)
        files = []
        for f in meta["fonts"]:
            if f["style"] != "normal" or not f["filename"].endswith(".ttf"):
                continue
            f["variable"] = "[" in f["filename"]
            files.append(f)
        # a variable font's glyf table IS its default instance; one sample
        variables = [f for f in files if f["variable"]]
        if variables:
            files = variables[:1]
        if files:
            selected.append({"dir": f"ofl/{d}", "name": meta["name"], "files": files})
    print(f"scanned {n_scanned} OFL families -> {len(selected)} sans-serif upright")
    return selected


def checkout_ttfs(selected):
    patterns = ["ofl/*/METADATA.pb"]
    for fam in selected:
        for f in fam["files"]:
            # sparse-checkout patterns are gitignore-style: bracket-named
            # variable fonts (Roboto[wdth,wght].ttf) need [ ] escaped or they
            # parse as character classes and silently match nothing
            escaped = f["filename"].replace("[", "\\[").replace("]", "\\]")
            patterns.append(f"{fam['dir']}/{escaped}")
    print(f"checking out {sum(len(f['files']) for f in selected)} ttf files "
          f"({len(selected)} families) -- blobs download on demand ...")
    p = subprocess.run(["git", "-C", CLONE_DIR, "sparse-checkout", "set", "--stdin"],
                       input="\n".join(patterns) + "\n", check=True, text=True, capture_output=True)
    return p


def write_manifest(selected, sha):
    missing = 0
    for fam in selected:
        for f in fam["files"]:
            path = os.path.join(CLONE_DIR, fam["dir"], f["filename"])
            if os.path.isfile(path):
                with open(path, "rb") as fh:
                    f["sha256"] = hashlib.sha256(fh.read()).hexdigest()
            else:
                f["sha256"] = None
                missing += 1
    manifest = {
        "upstream": UPSTREAM,
        "upstream_commit": sha,
        "license": "OFL",
        "category": "SANS_SERIF",
        "styles": "upright only (style == normal); variable fonts contribute their default instance",
        "families": selected,
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=1)
    n_files = sum(len(f["files"]) for f in selected)
    print(f"manifest: {len(selected)} families, {n_files} font files "
          f"({missing} missing on disk) -> {MANIFEST_PATH}")
    if missing:
        print("WARNING: missing files listed in METADATA.pb but absent from the repo; "
              "they carry sha256 null in the manifest and are skipped downstream.")


def main():
    sha = clone_metadata_stage()
    print(f"pinned upstream commit: {sha}")
    selected = select_families()
    checkout_ttfs(selected)
    write_manifest(selected, sha)


if __name__ == "__main__":
    sys.exit(main())
