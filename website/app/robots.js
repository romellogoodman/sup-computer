import { SITE_URL } from "../lib/content";

// Rendered to /robots.txt at build time. llms.txt (the LLM-readable index,
// ADR-0019) lives alongside it in public/.
export default function robots() {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
