import { notFound } from "next/navigation";
import { getReports, getReport, stripLeadIn } from "../../../lib/content";
import Markdown from "../../../components/Markdown";

export function generateStaticParams() {
  return getReports().map((r) => ({ slug: r.slug }));
}

export default function Report({ params }) {
  const r = getReport(params.slug);
  if (!r) return notFound();

  const { title, date, series } = r.frontmatter;
  const meta = [String(date || ""), series].filter(Boolean).join(" · ");

  return (
    <article>
      <h1>{title}</h1>
      <p className="meta">{meta}</p>
      <Markdown>{stripLeadIn(r.body)}</Markdown>
    </article>
  );
}
