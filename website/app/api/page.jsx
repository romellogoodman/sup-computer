import { notFound } from "next/navigation";
import { getPage, stripLeadIn } from "../../lib/content";
import Markdown from "../../components/Markdown";

// The API's root is its documentation: a page doc (ADR-0032) rendered at
// /api/, beside the functions in website/api/ that serve /api/models,
// /api/generate, and /api/health. See docs/adr/0036-hosted-inference-api.md.
export function generateMetadata() {
  const page = getPage("api");
  if (!page) return {};
  const { title, summary } = page.frontmatter;
  return {
    title,
    description: summary,
    openGraph: { title, description: summary, url: "/api/" },
    // llms.txt v2: advertise the markdown twin (ADR-0019) to agents
    alternates: { types: { "text/markdown": "/api.md" } },
  };
}

export default function Api() {
  const page = getPage("api");
  if (!page) return notFound();
  return (
    <article className="report">
      <h1 className="report__title">{page.frontmatter.title}</h1>
      <Markdown>{stripLeadIn(page.body)}</Markdown>
    </article>
  );
}
