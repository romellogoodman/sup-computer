import { notFound } from "next/navigation";
import { getReports, getReport, stripLeadIn, monthYear, researcherName } from "../../../lib/content";
import Markdown from "../../../components/Markdown";

export function generateStaticParams() {
  return getReports().map((r) => ({ slug: r.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const r = getReport(slug);
  if (!r) return {};
  const { title, summary, date } = r.frontmatter;
  return {
    title,
    description: summary,
    openGraph: {
      title,
      description: summary,
      type: "article",
      url: `/research/${r.slug}/`,
      publishedTime: date ? new Date(date).toISOString() : undefined,
    },
    // llms.txt v2: advertise the markdown twin (ADR-0019) to agents
    alternates: { types: { "text/markdown": `/research/${r.slug}.md` } },
  };
}

export default async function Report({ params }) {
  const { slug } = await params;
  const r = getReport(slug);
  if (!r) return notFound();

  const { title, type, date, series, researcher } = r.frontmatter;
  const meta = [
    type,
    monthYear(date),
    series,
    researcher && `researcher: ${researcherName(researcher)}`,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <article className="report">
      <h1 className="report__title">{title}</h1>
      <p className="report__meta">{meta}</p>
      <Markdown takeaways={r.frontmatter.takeaways}>{stripLeadIn(r.body)}</Markdown>
    </article>
  );
}
