"""fetch_poki.py -- clone the poki Lapo archive and keep only the
permissively-licensed works.

poki (https://github.com/kulupu-lapo/poki) is the community's curated archive
of long-form Toki Pona writing, 2002-2025. Licensing is **per work**, declared
in each file's frontmatter `license:` field. This script keeps a work only
when that field grants an explicit permissive licence (CC BY, CC BY-SA, CC0,
MIT, Public Domain) and drops everything else -- null, All Rights Reserved,
NC/ND variants, unknown strings. What was kept and dropped, per licence and
per work, is recorded in data/poki_audit.json (committed -- it is also the
attribution record for the corpus).

Writes: data/raw/poki.txt (one paragraph per line), data/poki_audit.json

Run from the repo root:
    uv run python projects/pona/data/fetch_poki.py
"""
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
REPO_URL = "https://github.com/kulupu-lapo/poki"
REPO_DIR = os.path.join(RAW, "poki")
OUT_PATH = os.path.join(RAW, "poki.txt")
AUDIT_PATH = os.path.join(HERE, "poki_audit.json")


def licence_verdict(value: str):
    """(kept: bool, normalized: str). Conservative: anything not an explicit
    permissive grant is dropped."""
    if value is None:
        return False, "null"
    norm = re.sub(r"[^A-Z0-9]", "", value.upper())
    if not norm or norm in ("NULL", "NONE", "UNKNOWNLICENSE", "UNKNOWN"):
        return False, "null"
    if "ALLRIGHTSRESERVED" in norm:
        return False, "all-rights-reserved"
    if "NC" in norm or "ND" in norm:
        return False, "cc-nonfree"
    if "CC0" in norm or "PUBLICDOMAIN" in norm:
        return True, "cc0/public-domain"
    if norm.startswith("MIT"):
        return True, "mit"
    if "CCBY" in norm:  # CC BY and CC BY-SA families, any version
        return True, "cc-by(-sa)"
    return False, f"unrecognized:{value.strip()}"


def parse_frontmatter(text: str):
    """Minimal YAML-ish frontmatter reader for the three fields the audit
    needs. Returns (fields, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    head, body = text[3:end], text[end + 4:]
    fields = {}
    for line in head.split("\n"):
        m = re.match(r"^(license|title|authors):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip().strip("'\"")
            fields[key] = val if val and val != "null" else None
        elif line.startswith("  - ") and "authors" in fields and not fields["authors"]:
            fields["authors"] = line[4:].strip()
        elif line.startswith("- ") and "authors" in fields.get("_last", ""):
            pass
    # authors as a block list: capture the first "- name" after the key
    m = re.search(r"^authors:\s*\n\s*-\s*(.+)$", head, flags=re.M)
    if m:
        fields["authors"] = m.group(1).strip()
    return fields, body


def body_paragraphs(body: str):
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)        # images
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)    # links -> label
    body = re.sub(r"^#{1,6}\s.*$", "", body, flags=re.M)    # headings
    body = body.replace("**", "").replace("*", "").replace("_", "")
    for block in body.split("\n\n"):
        para = re.sub(r"\s+", " ", block).strip()
        if len(para) >= 12:
            yield para


def main():
    os.makedirs(RAW, exist_ok=True)
    if not os.path.exists(REPO_DIR):
        print(f"cloning {REPO_URL} ...")
        subprocess.run(["git", "clone", "-q", "--depth", "1", REPO_URL, REPO_DIR], check=True)
    commit = subprocess.run(["git", "-C", REPO_DIR, "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()

    kept_works, dropped = [], {}
    lines = []
    plaintext = os.path.join(REPO_DIR, "plaintext")
    for root, _, files in sorted(os.walk(plaintext)):
        for name in sorted(files):
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8") as f:
                fields, body = parse_frontmatter(f.read())
            ok, norm = licence_verdict(fields.get("license"))
            rel = os.path.relpath(path, REPO_DIR)
            if ok:
                paras = list(body_paragraphs(body))
                lines.extend(paras)
                kept_works.append({
                    "file": rel,
                    "title": fields.get("title"),
                    "author": fields.get("authors"),
                    "license": (fields.get("license") or "").strip(),
                    "paragraphs": len(paras),
                })
            else:
                dropped[norm] = dropped.get(norm, 0) + 1

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    audit = {
        "source": REPO_URL,
        "commit": commit,
        "policy": "explicit permissive grants only (CC BY / CC BY-SA / CC0 / MIT / Public Domain); "
                  "null, All Rights Reserved, NC and ND variants dropped",
        "kept_works": len(kept_works),
        "dropped_by_reason": dropped,
        "works": kept_works,
    }
    with open(AUDIT_PATH, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)
    n_chars = sum(len(l) + 1 for l in lines)
    print(f"kept {len(kept_works)} works ({len(lines):,} paragraphs, {n_chars:,} chars)")
    print(f"dropped: {dropped}")
    print(f"wrote {OUT_PATH} and {AUDIT_PATH}")


if __name__ == "__main__":
    main()
