"""fetch_wikipedia.py -- download the Toki Pona Wikipedia dump and flatten it
to plain paragraphs.

Source: https://dumps.wikimedia.org/tokwiki/ (CC BY-SA). The dump is ~3MB
compressed; article namespace only, redirects skipped, wikitext stripped with
a small regex cleaner. Anything the cleaner misses is caught downstream by
build_corpus.py's sonatoki filter -- this stage only has to get the bulk out.

Writes: data/raw/wikipedia.txt (one paragraph per line)

Run from the repo root:
    uv run python projects/pona/data/fetch_wikipedia.py
"""
import bz2
import html
import os
import re
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
DUMP_URL = "https://dumps.wikimedia.org/tokwiki/latest/tokwiki-latest-pages-articles.xml.bz2"
DUMP_PATH = os.path.join(RAW, "tokwiki-latest-pages-articles.xml.bz2")
OUT_PATH = os.path.join(RAW, "wikipedia.txt")


def strip_wikitext(text: str) -> str:
    # templates {{...}}, innermost out (bounded loop: pathological nesting just
    # leaves residue for the sonatoki filter to drop)
    for _ in range(20):
        stripped = re.sub(r"\{\{[^{}]*\}\}", "", text)
        if stripped == text:
            break
        text = stripped
    # tables
    text = re.sub(r"\{\|.*?\|\}", "", text, flags=re.S)
    # comments, refs, media/markup blocks, then all remaining tags
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<ref[^>/]*/>", "", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"<(gallery|timeline|score|syntaxhighlight|source|math|nowiki|imagemap)[^>]*>.*?</\1>",
                  "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "", text)
    # media/category links (tok wiki localizes File:/Category: as sitelen:/kulupu:)
    text = re.sub(r"\[\[(?:[Ff]ile|[Ii]mage|[Ss]itelen|[Kk]ulupu|[Cc]ategory)\s*:[^\[\]]*(?:\[\[[^\[\]]*\]\][^\[\]]*)*\]\]",
                  "", text)
    # interwiki/language links like [[en:Foo]]
    text = re.sub(r"\[\[[a-z-]{2,12}:[^\[\]]*\]\]", "", text)
    # piped link -> label, plain link -> target
    text = re.sub(r"\[\[[^\[\]|]*\|([^\[\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\[\]]*)\]\]", r"\1", text)
    # external links
    text = re.sub(r"\[https?://[^\s\]]+\s+([^\]]*)\]", r"\1", text)
    text = re.sub(r"\[?https?://[^\s\]]+\]?", "", text)
    # bold/italic markup
    text = text.replace("'''", "").replace("''", "")
    return text


def page_paragraphs(text: str):
    text = strip_wikitext(text)
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        # headings, list/table residue, magic words
        if not line or line.startswith(("=", "|", "!", "{", "}", "__")):
            continue
        line = re.sub(r"^[*#:;]+\s*", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) >= 12:
            yield line


def main():
    os.makedirs(RAW, exist_ok=True)
    if not os.path.exists(DUMP_PATH):
        print(f"downloading {DUMP_URL} ...")
        urllib.request.urlretrieve(DUMP_URL, DUMP_PATH)
    print(f"dump: {os.path.getsize(DUMP_PATH):,} bytes")

    pages = kept_pages = 0
    lines = []
    with bz2.open(DUMP_PATH, "rb") as f:
        for _, elem in ET.iterparse(f):
            if not elem.tag.endswith("}page"):
                continue
            pages += 1
            ns = elem.find("./{*}ns")
            redirect = elem.find("./{*}redirect")
            text_el = elem.find("./{*}revision/{*}text")
            if ns is not None and ns.text == "0" and redirect is None \
                    and text_el is not None and text_el.text:
                body = html.unescape(text_el.text)
                if not re.match(r"^\s*#", body):  # leftover redirect styles
                    page_lines = list(page_paragraphs(body))
                    if page_lines:
                        kept_pages += 1
                        lines.extend(page_lines)
            elem.clear()

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    n_chars = sum(len(line) + 1 for line in lines)
    print(f"pages seen: {pages:,}  articles kept: {kept_pages:,}")
    print(f"wrote {len(lines):,} paragraphs, {n_chars:,} chars -> {OUT_PATH}")


if __name__ == "__main__":
    main()
