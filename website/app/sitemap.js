import { getReports, getRegistry } from "../lib/content";

// Canonical absolute base for the sitemap entries. No production domain is pinned
// anywhere in the repo yet (next.config emits a static site that's "deployable
// anywhere"), so it's env-driven: set NEXT_PUBLIC_SITE_URL at build time. The
// default is a placeholder. The trailing slash is trimmed so paths join cleanly;
// the routes themselves keep their trailing slash to match next.config's
// trailingSlash: true.
const BASE = (process.env.NEXT_PUBLIC_SITE_URL || "https://sup.computer").replace(/\/$/, "");

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
    ...reports.map((r) => ({
      url: `${BASE}/research/${r.slug}/`,
      lastModified: r.frontmatter.date ? new Date(r.frontmatter.date) : undefined,
    })),
    ...models.map((m) => ({
      url: `${BASE}/models/${m.id}/`,
    })),
  ];
}
