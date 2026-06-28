import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";

const ROOT = path.join(process.cwd(), "content");
const REPORTS = path.join(ROOT, "research-docs", "reports");
const CARDS = path.join(ROOT, "research-docs", "model-cards");

// Chart paths in the markdown ("assets/x.png", "../reports/assets/x.png") are
// rewritten to the served location (public/research-assets/ -> /research-assets/).
const rewriteAssets = (s) => s.replace(/(?:[.\w-]+\/)*assets\//g, "/research-assets/");

const GITHUB = "https://github.com/romellogoodman/sup-computer";

// Resolve one relative markdown link target (written relative to the doc's repo
// location) to where the *site* should point. The reports cite their own receipts
// with repo-relative paths so the .md stays portable in-repo and on GitHub; on the
// site those paths are meaningless, so we rewrite them at sync time:
//   - sibling report      -> /research/<slug>/        (README -> the home index)
//   - a model card         -> /models/<id>/
//   - any other repo path  -> a GitHub blob/tree URL on main
// External (http, mailto), in-page (#anchor) and already-absolute (/served) links
// are left untouched.
function resolveLink(target, repoBase) {
  if (/^(https?:|mailto:|tel:|#|\/)/.test(target)) return null;
  const [rawPath, frag] = target.split("#");
  const hash = frag ? `#${frag}` : "";
  if (!rawPath) return null; // bare "#anchor" already handled above
  const isDir = rawPath.endsWith("/");
  const resolved = path.posix.normalize(path.posix.join(repoBase, rawPath)).replace(/\/$/, "");

  let m;
  if ((m = resolved.match(/^research-docs\/reports\/([^/]+)\.md$/))) {
    return m[1] === "README" ? `/#research${hash}` : `/research/${m[1]}/${hash}`;
  }
  if ((m = resolved.match(/^research-docs\/model-cards\/([^/]+)\.md$/))) {
    return `/models/${m[1]}/${hash}`;
  }
  // A path with no file extension on its last segment is treated as a directory.
  const kind = isDir || !path.posix.basename(resolved).includes(".") ? "tree" : "blob";
  return `${GITHUB}/${kind}/main/${resolved}${hash}`;
}

// Rewrite every markdown link destination `](target)` in a doc. `repoBase` is the
// doc's directory relative to the repo root (e.g. "research-docs/reports"), used to
// resolve "../../" paths. Image paths were already turned into /research-assets/ by
// rewriteAssets and so begin with "/" — resolveLink leaves those alone.
function rewriteLinks(body, repoBase) {
  return body.replace(/(\]\()([^)\s]+)((?:\s+"[^"]*")?\))/g, (full, open, target, close) => {
    const next = resolveLink(target, repoBase);
    return next ? `${open}${next}${close}` : full;
  });
}

// Drop everything up to and including the first H1 (a repo breadcrumb + the title
// that the page re-renders from frontmatter/registry).
export function stripLeadIn(body) {
  const lines = body.split("\n");
  const i = lines.findIndex((l) => /^#\s+/.test(l));
  return i >= 0 ? lines.slice(i + 1).join("\n").replace(/^\s+/, "") : body;
}

// `repoBase` is the directory's path relative to the repo root, so the link
// rewriter can resolve the repo-relative "../../" targets the docs are written with.
function readDir(dir, repoBase) {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md") && f !== "README.md")
    .map((f) => {
      const { data, content } = matter(fs.readFileSync(path.join(dir, f), "utf8"));
      const body = rewriteLinks(rewriteAssets(content), repoBase);
      return { slug: f.replace(/\.md$/, ""), frontmatter: data, body };
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
  return readDir(REPORTS, "research-docs/reports").sort((a, b) => writtenAt(b) - writtenAt(a));
}
export function getReport(slug) {
  return getReports().find((r) => r.slug === slug);
}

export function getRegistry() {
  const p = path.join(ROOT, "registry.json");
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : { models: [] };
}

// The AI researcher credited on an artifact. Reports carry a `researcher` id in
// frontmatter; models carry one in registry.json. Both resolve through the shared
// `researchers` map to a display name. See docs/adr/0013-attribution-of-the-ai-researcher.md.
export function getResearchers() {
  return getRegistry().researchers || {};
}
export function researcherName(id) {
  if (!id) return "";
  return getResearchers()[id]?.name || id;
}

export function getCard(id) {
  return readDir(CARDS, "research-docs/model-cards").find((c) => c.slug === id);
}
