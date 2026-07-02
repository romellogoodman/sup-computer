"""Repo integrity check: the manifest and the docs must match the tree.

Catches the drift class that creeps in when docs and registry.json are written
by hand (or by an agent): claimed git tags that don't exist, frozen_code /
model_card paths that moved, markdown links that 404, released models missing
their MODELS.md / leaderboard.md records, and weight files accidentally
tracked. Pure stdlib; safe to run anywhere in the repo:

    python3 tools/check_integrity.py

Exits 0 when clean, 1 with a findings list otherwise. Wire it into CI and run
it before committing doc or registry changes.
"""

import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# markdown trees we don't own or that are generated
SKIP_DIRS = {".git", ".venv", "node_modules", "content", "output", ".next"}
SKIP_PREFIXES = ("website/public",)

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")
WEIGHT_EXTS = (".pt", ".bin", ".onnx", ".pkl")


def fail(findings, msg):
    findings.append(msg)


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    ).stdout.splitlines()


def check_registry(findings):
    reg_path = os.path.join(ROOT, "registry.json")
    with open(reg_path, encoding="utf-8") as f:
        reg = json.load(f)
    tags = set(git("tag", "-l"))
    researchers = set(reg.get("researchers", {}))
    for m in reg.get("models", []):
        mid = m.get("id", "<no id>")
        if m.get("git_tag") not in tags:
            fail(findings, f"registry: {mid}: git tag {m.get('git_tag')!r} does not exist")
        frozen = m.get("frozen_code", "")
        if not os.path.isdir(os.path.join(ROOT, frozen)):
            fail(findings, f"registry: {mid}: frozen_code {frozen!r} is not a directory")
        else:
            for required in ("model.py", "train.py", "README.md"):
                if not os.path.exists(os.path.join(ROOT, frozen, required)):
                    fail(findings, f"registry: {mid}: frozen_code missing {required}")
        card = m.get("model_card", "")
        if not os.path.isfile(os.path.join(ROOT, card)):
            fail(findings, f"registry: {mid}: model_card {card!r} does not exist")
        if m.get("researcher") not in researchers:
            fail(findings, f"registry: {mid}: researcher {m.get('researcher')!r} not in researchers map")
        project = m.get("project", "")
        for record in ("MODELS.md", "leaderboard.md", "README.md", "CLAUDE.md"):
            if not os.path.exists(os.path.join(ROOT, "projects", project, record)):
                fail(findings, f"registry: {mid}: projects/{project}/ missing {record}")


def markdown_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel = os.path.relpath(dirpath, ROOT)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if any(rel == p or rel.startswith(p + os.sep) for p in SKIP_PREFIXES):
            dirnames[:] = []
            continue
        for name in filenames:
            if name.endswith(".md"):
                yield os.path.join(dirpath, name)


def check_links(findings):
    for path in markdown_files():
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        # fenced code blocks routinely show example paths that aren't links
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = os.path.normpath(os.path.join(os.path.dirname(path), target))
            if not os.path.exists(resolved):
                fail(findings, f"link: {rel}: broken relative link -> {target}")


def check_no_tracked_weights(findings):
    for tracked in git("ls-files"):
        if tracked.endswith(WEIGHT_EXTS):
            fail(findings, f"weights: {tracked} is git-tracked (violates the no-weights rule)")


def main():
    findings = []
    check_registry(findings)
    check_links(findings)
    check_no_tracked_weights(findings)
    if findings:
        print(f"INTEGRITY: {len(findings)} finding(s)\n" + "\n".join(f"  - {f}" for f in findings))
        return 1
    print("INTEGRITY: clean (registry, links, weights)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
