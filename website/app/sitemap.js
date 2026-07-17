import { getReports, getRegistry, SITE_URL } from "../lib/content";

// Canonical absolute base for the sitemap entries (shared with the .md generator).
// The routes keep their trailing slash to match next.config's trailingSlash: true.
const BASE = SITE_URL;

// Enumerate the real routes from the same sources the pages read: the static home,
// one page per research report (getReports), and one per model (registry.json).
// Next.js renders this to /sitemap.xml at build time.
export default function sitemap() {
  const reports = getReports();
  const { models } = getRegistry();

  // The newest report stands in as the home page's lastModified.
  const latest = reports[0]?.frontmatter.date;

  return [
    { url: `${BASE}/`, lastModified: latest ? new Date(latest) : undefined },
    { url: `${BASE}/train/` },
    ...reports.map((r) => ({
      url: `${BASE}/research/${r.slug}/`,
      lastModified: r.frontmatter.date ? new Date(r.frontmatter.date) : undefined,
    })),
    ...models.map((m) => ({
      url: `${BASE}/models/${m.id}/`,
    })),
  ];
}
