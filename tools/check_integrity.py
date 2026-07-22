"""Repo integrity check: the manifest and the docs must match the tree.

Catches the drift class that creeps in when docs and registry.json are written
by hand (or by an agent): claimed git tags that don't exist, frozen_code /
model_card paths that moved, markdown links that 404, released models missing
their README Versions/Leaderboard records (ADR-0030), stale generated index
tables (ADR-0033), and weight files accidentally tracked. Pure stdlib; safe to
run anywhere in the repo:

    python3 tools/check_integrity.py            # check (CI runs this)
    python3 tools/check_integrity.py --write    # regenerate the index tables

The three index tables (reports, ADRs, tools) are generated, not hand-edited:
--write derives them from report frontmatter, ADR headers, and tool
taglines/docstrings, rewriting the <!-- generated:NAME --> blocks in place.
Exits 0 when clean, 1 with a findings list otherwise.
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
        readme = os.path.join(ROOT, "projects", project, "README.md")
        if not os.path.exists(readme):
            fail(findings, f"registry: {mid}: projects/{project}/ missing README.md")
        else:
            with open(readme, encoding="utf-8") as f:
                text = f.read()
            # ADR-0030: the README carries the version index and scoreboard,
            # and every released model appears in it by id.
            for section in ("## Versions", "## Leaderboard"):
                if section not in text:
                    fail(findings, f"registry: projects/{project}/README.md missing '{section}' section")
            if mid not in text:
                fail(findings, f"registry: {mid} not mentioned in projects/{project}/README.md")
        if not os.path.exists(os.path.join(ROOT, "projects", project, "CLAUDE.md")):
            fail(findings, f"registry: {mid}: projects/{project}/ missing CLAUDE.md")


# --- generated index tables (ADR-0033) -------------------------------------
# The three index tables are derived from their sources, not hand-maintained:
# report frontmatter, ADR headers, tool taglines/docstrings. `--write`
# regenerates them between <!-- generated:NAME --> markers; check mode fails
# a stale or missing block.

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def cell(s):
    return s.replace("|", "\\|")


def parse_frontmatter(path):
    """Minimal stdlib frontmatter reader: scalar keys plus folded (>) blocks."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm = {}
    i = 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val in (">", ">-", "|", "|-", ""):
                block = []
                j = i + 1
                while j < len(lines):
                    cont = lines[j]
                    if cont.strip() and not cont.startswith(" "):
                        break
                    if cont.strip():
                        block.append(cont.strip())
                    j += 1
                fm[key] = " ".join(block)
                i = j
                continue
            fm[key] = val.strip('"').strip("'")
        i += 1
    return fm


def gen_reports_index(findings):
    reports_dir = os.path.join(ROOT, "research-docs", "reports")
    with open(os.path.join(ROOT, "registry.json"), encoding="utf-8") as f:
        researchers = json.load(f).get("researchers", {})
    rows = []
    for name in sorted(os.listdir(reports_dir)):
        if not name.endswith(".md") or name == "README.md":
            continue
        fm = parse_frontmatter(os.path.join(reports_dir, name))
        date_raw = fm.get("date", "")
        # dates must carry a time: the site sorts by timestamp and shows
        # month+year, and same-day publishes are common — a date-only value
        # turns the ordering into an alphabetical accident
        if not re.match(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", date_raw):
            fail(findings, f"reports: {name} frontmatter date lacks a publish time "
                           f"(want YYYY-MM-DDTHH:MM[:SS][offset])")
        rid = fm.get("researcher", "")
        if rid not in researchers:
            fail(findings, f"reports: {name} researcher {rid!r} not in registry researchers map")
        num = f"{int(fm['number']):02d}" if fm.get("number", "").isdigit() else "—"
        marker = ""
        if fm.get("type") == "note":
            marker = f"*note, series: {fm['series']}*. " if fm.get("series") else "*note*. "
        blurb = " ".join(fm.get("summary", "").split())
        date = (f"{MONTHS[int(date_raw[5:7]) - 1]} {date_raw[:4]}"
                if re.match(r"\d{4}-\d{2}", date_raw) else "—")
        rows.append((date_raw, f"| {num} | [{cell(fm.get('title', name))}]({name}) — "
                              f"{marker}{cell(blurb)} | {cell(fm.get('produced') or '—')} | "
                              f"{researchers.get(rid, {}).get('name', rid or '—')} | {date} |"))
    rows.sort(key=lambda r: r[0])
    return ("| # | Report | Produced | Researcher | Date |\n"
            "|---|--------|----------|-----------|------|\n"
            + "\n".join(r[1] for r in rows))


def gen_adr_index(findings):
    adr_dir = os.path.join(ROOT, "docs", "adr")
    rows = []
    for name in sorted(os.listdir(adr_dir)):
        if not re.match(r"\d{4}-.+\.md$", name):
            continue
        with open(os.path.join(adr_dir, name), encoding="utf-8") as f:
            head = f.read(4096).splitlines()
        title = next((l[len(f"# ADR {name[:4]}: "):] for l in head
                      if re.match(r"^# ADR \d{4}: ", l)), None)
        status = None
        for i, l in enumerate(head):
            m = re.match(r"^- \*\*Status:\*\* (.+)$", l)
            if m:
                parts = [m.group(1)]
                # a wrapped status bullet continues on two-space-indented lines
                for cont in head[i + 1:]:
                    if not cont.startswith("  "):
                        break
                    parts.append(cont.strip())
                status = " ".join(parts)
                break
        if not title or not status:
            fail(findings, f"adr: {name} lacks the '# ADR NNNN: <title>' H1 or '**Status:**' line")
            continue
        rows.append(f"| [{name[:4]}]({name}) | {cell(title)} | {cell(status)} |")
    return "| # | Decision | Status |\n|---|---|---|\n" + "\n".join(rows)


def tagline_of(findings, rel, text):
    """First italic line after the H1 — the file's own one-line description."""
    for line in text.splitlines()[1:]:
        if not line.strip():
            continue
        if line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            return line[1:-1]
        break
    fail(findings, f"tools: {rel} has no tagline (an italic line right under the H1)")
    return ""


def gen_tools_index(findings):
    tools_dir = os.path.join(ROOT, "tools")
    rows = []
    for name in sorted(os.listdir(tools_dir)):
        path = os.path.join(tools_dir, name)
        if os.path.isdir(path) and not name.startswith((".", "_")):
            readme = os.path.join(path, "README.md")
            if not os.path.isfile(readme):
                fail(findings, f"tools: tools/{name}/ has no README.md")
                continue
            with open(readme, encoding="utf-8") as f:
                tag = tagline_of(findings, f"tools/{name}/README.md", f.read())
            rows.append(f"| [`{name}/`]({name}/) | {cell(tag)} |")
        elif name.endswith(".py"):
            with open(path, encoding="utf-8") as f:
                doc = re.search(r'"""(.*?)"""', f.read(), re.S)
            if not doc:
                fail(findings, f"tools: tools/{name} has no module docstring")
                continue
            first = " ".join(doc.group(1).split()).split(". ")[0].rstrip(".") + "."
            rows.append(f"| [`{name}`]({name}) | {cell(first)} |")
    return "| Tool | What it is |\n|---|---|\n" + "\n".join(rows)


GENERATED = [
    ("research-docs/reports/README.md", "reports-index", gen_reports_index),
    ("docs/adr/README.md", "adr-index", gen_adr_index),
    ("tools/README.md", "tools-index", gen_tools_index),
]


def check_generated(findings, write=False):
    for rel, tag, gen in GENERATED:
        expected = gen(findings)
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        m = re.search(rf"(<!-- generated:{tag} -->\n).*?(\n<!-- /generated -->)", text, re.S)
        if not m:
            fail(findings, f"index: {rel} has no <!-- generated:{tag} --> block")
            continue
        if text[m.end(1):m.start(2)] != expected:
            if write:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text[:m.end(1)] + expected + text[m.start(2):])
                print(f"wrote {rel}")
            else:
                fail(findings, f"index: {rel} generated block is stale — "
                               f"run `python3 tools/check_integrity.py --write`")


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
    write = "--write" in sys.argv[1:]
    findings = []
    check_registry(findings)
    check_generated(findings, write=write)
    check_links(findings)
    check_no_tracked_weights(findings)
    if findings:
        print(f"INTEGRITY: {len(findings)} finding(s)\n" + "\n".join(f"  - {f}" for f in findings))
        return 1
    print("INTEGRITY: clean (registry, indexes, links, weights)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
