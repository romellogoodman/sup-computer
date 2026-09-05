// Emit /sitemap.xml as a plain static file in public/.
//
// The site is a static export, and Next 14's sitemap.js metadata route is
// dynamic under the hood (/sitemap.xml/[[...__metadata_id__]]): the built
// site was fine, but the dev server refused it with "missing
// generateStaticParams" under output: "export". A file in public/ has no
// route to refuse and ships verbatim in the export, so the sitemap is
// generated here, from the same sources the pages read, in the prebuild
// chain beside llms.txt (build-text.mjs).

import { writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { getReports, getRegistry, getSeries, seriesHref, SITE_URL } from "../lib/content.js";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "..", "public", "sitemap.xml");

// Routes keep their trailing slash to match next.config's trailingSlash: true.
const reports = getReports();
const { models } = getRegistry();
const latest = reports[0]?.frontmatter.date; // the newest report stands in for the home page

const iso = (d) => (d ? new Date(d).toISOString() : null);
const entries = [
  { url: `${SITE_URL}/`, lastmod: iso(latest) },
  { url: `${SITE_URL}/research/`, lastmod: iso(latest) },
  { url: `${SITE_URL}/train/` },
  ...getSeries().map((s) => ({ url: `${SITE_URL}${seriesHref(s)}` })),
  ...reports.map((r) => ({ url: `${SITE_URL}/research/${r.slug}/`, lastmod: iso(r.frontmatter.date) })),
  ...models.map((m) => ({ url: `${SITE_URL}/models/${m.id}/` })),
];

const xml =
  `<?xml version="1.0" encoding="UTF-8"?>\n` +
  `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
  entries
    .map((e) => `  <url>\n    <loc>${e.url}</loc>\n${e.lastmod ? `    <lastmod>${e.lastmod}</lastmod>\n` : ""}  </url>`)
    .join("\n") +
  `\n</urlset>\n`;

await writeFile(out, xml);
console.log(`wrote sitemap.xml (${entries.length} urls) -> public/`);
