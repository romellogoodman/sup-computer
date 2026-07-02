import { notFound } from "next/navigation";
import { getReports, getReport, stripLeadIn, monthYear, researcherName } from "../../../lib/content";
import Markdown from "../../../components/Markdown";

export function generateStaticParams() {
  return getReports().map((r) => ({ slug: r.slug }));
}

export function generateMetadata({ params }) {
  const r = getReport(params.slug);
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
  };
}

export default function Report({ params }) {
  const r = getReport(params.slug);
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
      <p className="report__back"><a href="/#research">← research</a></p>
      <h1 className="report__title">{title}</h1>
      <p className="report__meta">{meta}</p>
      <Markdown>{stripLeadIn(r.body)}</Markdown>
    </article>
  );
}
