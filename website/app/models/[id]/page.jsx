import { notFound } from "next/navigation";
import { getRegistry, getCard, stripLeadIn, getSeries, seriesHref } from "../../../lib/content";
import Markdown from "../../../components/Markdown";
import SpecTable from "../../../components/SpecTable";

// /models/<id>/ — one release: the registry facts, then the model card.
// Unchanged in shape because published reports cite these URLs; the series
// page it belongs to lives at /<project>/ (ADR-0035).

export function generateStaticParams() {
  return getRegistry().models.map((m) => ({ id: m.id }));
}

export function generateMetadata({ params }) {
  const m = getRegistry().models.find((x) => x.id === params.id);
  if (!m) return {};
  const description = `${m.architecture} · ${m.tokenizer.type} tokenizer · ${m.params.toLocaleString("en-US")} parameters`;
  return {
    title: m.id,
    description,
    openGraph: { title: m.id, description, url: `/models/${m.id}/` },
    // llms.txt v2: advertise the markdown twin (ADR-0019) to agents
    alternates: { types: { "text/markdown": `/models/${m.id}.md` } },
  };
}

export default function Model({ params }) {
  const m = getRegistry().models.find((x) => x.id === params.id);
  if (!m) return notFound();
  const card = getCard(m.id);
  const seriesOf = getSeries().find((s) => s.project === m.project);

  return (
    <>
      <h1 className="model__title">{m.id}</h1>
      {seriesOf && (
        <p className="model__series">
          a release of <a href={seriesHref(seriesOf)}>{seriesOf.name}</a>
        </p>
      )}
      <SpecTable m={m} />
      {card && (
        <>
          <hr />
          <Markdown>{stripLeadIn(card.body)}</Markdown>
        </>
      )}
    </>
  );
}
