import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";

const ROOT = path.join(process.cwd(), "content");
const REPORTS = path.join(ROOT, "research-docs", "reports");
const CARDS = path.join(ROOT, "research-docs", "model-cards");

// Chart paths in the markdown ("assets/x.png", "../reports/assets/x.png") are
// rewritten to the served location (public/research-assets/ -> /research-assets/).
const rewriteAssets = (s) => s.replace(/(?:[.\w-]+\/)*assets\//g, "/research-assets/");

// Drop everything up to and including the first H1 (a repo breadcrumb + the title
// that the page re-renders from frontmatter/registry).
export function stripLeadIn(body) {
  const lines = body.split("\n");
  const i = lines.findIndex((l) => /^#\s+/.test(l));
  return i >= 0 ? lines.slice(i + 1).join("\n").replace(/^\s+/, "") : body;
}

function readDir(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md") && f !== "README.md")
    .map((f) => {
      const { data, content } = matter(fs.readFileSync(path.join(dir, f), "utf8"));
      return { slug: f.replace(/\.md$/, ""), frontmatter: data, body: rewriteAssets(content) };
    });
}

// Newest first. gray-matter parses YAML `date:` into a Date object, so compare by
// timestamp — a string/localeCompare sort orders by weekday name, not chronology.
const writtenAt = (r) => (r.frontmatter.date ? new Date(r.frontmatter.date).getTime() : 0);

// "June 2026". UTC so a YAML date (parsed as midnight UTC) doesn't shift a day back
// in a negative-offset timezone and land in the previous month.
export function monthYear(date) {
  if (!date) return "";
  return new Date(date).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}
export function getReports() {
  return readDir(REPORTS).sort((a, b) => writtenAt(b) - writtenAt(a));
}
export function getReport(slug) {
  return getReports().find((r) => r.slug === slug);
}

export function getRegistry() {
  const p = path.join(ROOT, "registry.json");
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : { models: [] };
}

export function getCard(id) {
  return readDir(CARDS).find((c) => c.slug === id);
}
