import { SITE_URL } from "../lib/content";

// Rendered to /robots.txt at build time. llms.txt (the LLM-readable index,
// ADR-0019) lives alongside it in public/. output: "export" needs the route
// marked static explicitly (Next 15+).
export const dynamic = "force-static";

export default function robots() {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
