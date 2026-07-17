import { notFound } from "next/navigation";
import { getPage, stripLeadIn } from "../../lib/content";
import Markdown from "../../components/Markdown";
import PromptBlock from "../../components/PromptBlock";

export function generateMetadata() {
  const page = getPage("train");
  if (!page) return {};
  const { title, summary } = page.frontmatter;
  return {
    title,
    description: summary,
    openGraph: { title, description: summary, url: "/train/" },
  };
}

// The doc's first fenced code block is the prompt; it renders through
// PromptBlock (copy button, raw text) and the prose around it as normal
// markdown. See docs/adr/0032-train-page-prompt-as-content.md.
const FENCE = /^```[^\n]*\n([\s\S]*?)\n```$/m;

export default function Train() {
  const page = getPage("train");
  if (!page) return notFound();

  const body = stripLeadIn(page.body);
  const m = body.match(FENCE);
  const before = m ? body.slice(0, m.index) : body;
  const after = m ? body.slice(m.index + m[0].length) : "";

  return (
    <article className="report">
      <h1 className="report__title">{page.frontmatter.title}</h1>
      <Markdown>{before}</Markdown>
      {m && <PromptBlock text={m[1]} />}
      {after.trim() && <Markdown>{after}</Markdown>}
    </article>
  );
}
