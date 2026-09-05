import { notFound } from "next/navigation";
import {
  getRegistry,
  getCard,
  stripLeadIn,
  researcherName,
  getSeries,
  getSeriesBySlug,
  reportsForSeries,
  reportTier,
  versionLabel,
} from "../../../lib/content";
import Markdown from "../../../components/Markdown";
import Instrument from "../../../components/instruments/Instrument";
import CardDetails from "../../../components/CardDetails";
import { ReportItem } from "../../../components/ReportList";

// Two kinds of page share this route (ADR-0035):
//   /models/<series>/   the series page — instrument first, wired to the
//                       newest release; then specs, releases, lab notes, and
//                       the demoted model card
//   /models/<id>/       one release — unchanged, because published reports
//                       cite these URLs
// A series slug is a release id minus its version, so the two never collide.

export function generateStaticParams() {
  return [
    ...getSeries().map((s) => ({ id: s.slug })),
    ...getRegistry().models.map((m) => ({ id: m.id })),
  ];
}

const specLine = (m) =>
  `${m.architecture} · ${m.tokenizer.type} tokenizer · ${m.params.toLocaleString("en-US")} parameters`;

export function generateMetadata({ params }) {
  const series = getSeriesBySlug(params.id);
  if (series) {
    return {
      title: series.name,
      description: series.tagline,
      openGraph: { title: series.name, description: series.tagline, url: `/models/${series.slug}/` },
    };
  }
  const m = getRegistry().models.find((x) => x.id === params.id);
  if (!m) return {};
  const description = specLine(m);
  return {
    title: m.id,
    description,
    openGraph: { title: m.id, description, url: `/models/${m.id}/` },
  };
}

// checkpoint is an HF resolve URL (…/sup-computer/<id>/resolve/main/ckpt.pt);
// link the repo page, not the raw file
const hfRepoOf = (m) => m.artifacts?.checkpoint?.replace(/\/resolve\/.*$/, "");

function SpecTable({ m, showRelease }) {
  const hfRepo = hfRepoOf(m);
  return (
    <table className="spec-table">
      <tbody>
        {showRelease ? (
          <tr>
            <th>Release</th>
            <td>
              <a href={`/models/${m.id}/`}>{m.id}</a>
            </td>
          </tr>
        ) : (
          <tr><th>Series</th><td>{m.project}</td></tr>
        )}
        <tr><th>Version</th><td>{m.version}</td></tr>
        <tr><th>Git tag</th><td>{m.git_tag}</td></tr>
        <tr><th>Architecture</th><td>{m.architecture}</td></tr>
        <tr><th>Tokenizer</th><td>{`${m.tokenizer.type} (${m.tokenizer.vocab_size})`}</td></tr>
        <tr><th>Parameters</th><td>{m.params.toLocaleString("en-US")}</td></tr>
        <tr><th>Held-out BPC</th><td>{m.held_out_bpc != null ? m.held_out_bpc : "—"}</td></tr>
        <tr>
          <th>Weights</th>
          <td>
            {hfRepo ? (
              <a href={hfRepo}>{hfRepo.replace("https://huggingface.co/", "")} (Hugging Face)</a>
            ) : (
              "—"
            )}
          </td>
        </tr>
        <tr><th>Researcher</th><td>{m.researcher ? researcherName(m.researcher) : "—"}</td></tr>
      </tbody>
    </table>
  );
}

function SeriesPage({ series }) {
  const { slug, name, tagline, verb, instrument, flagship, versions, latest } = series;
  const card = getCard(flagship.id);
  const filed = reportsForSeries(series);
  const essays = filed.filter((r) => reportTier(r) === "essay");
  const labNotes = filed.filter((r) => reportTier(r) === "lab-note");
  const playable = latest.map((m) => m.id);

  return (
    <>
      <h1 className="series__title">{name}</h1>
      <p className="series__tagline">{tagline}</p>

      <Instrument kind={instrument} series={{ slug, name, tagline, verb }} models={latest} />

      <h2 className="section-label series__section" id="specs">Specs</h2>
      <SpecTable m={flagship} showRelease />
      {latest.length > 1 && (
        <p className="section-note">
          The instrument runs {playable.length} sibling releases:{" "}
          {latest.map((m, i) => (
            <span key={m.id}>
              {i > 0 && ", "}
              <a href={`/models/${m.id}/`}>{versionLabel(m, slug)}</a>
            </span>
          ))}
          . The specs above are the base tier's.
        </p>
      )}

      <h2 className="section-label series__section" id="releases">Releases</h2>
      <ul className="release-list">
        {versions.map((m) => (
          <li className="release-list__item" key={m.id}>
            <span className="release-list__version">{versionLabel(m, slug)}</span>
            <span>
              <a href={`/models/${m.id}/`}>{m.id}</a>
              {m.tagline && <span className="release-list__tagline"> — {m.tagline}</span>}
            </span>
          </li>
        ))}
      </ul>

      {essays.length > 0 && (
        <>
          <h2 className="section-label series__section" id="essays">Essays</h2>
          {essays.map((r) => (
            <ReportItem key={r.slug} report={r} />
          ))}
        </>
      )}

      <h2 className="section-label series__section" id="lab-notes">Lab notes</h2>
      {labNotes.length ? (
        labNotes.map((r) => <ReportItem key={r.slug} report={r} />)
      ) : (
        <p className="section-note">No lab notes filed under this series yet.</p>
      )}

      {card && (
        <>
          <h2 className="section-label series__section" id="card">Model card</h2>
          <CardDetails summary={`${flagship.id} — the release's model card`}>
            <Markdown>{stripLeadIn(card.body)}</Markdown>
          </CardDetails>
        </>
      )}
    </>
  );
}

export default function Page({ params }) {
  const series = getSeriesBySlug(params.id);
  if (series) return <SeriesPage series={series} />;

  const m = getRegistry().models.find((x) => x.id === params.id);
  if (!m) return notFound();
  const card = getCard(m.id);
  const seriesOf = getSeries().find((s) => s.project === m.project);

  return (
    <>
      <h1 className="model__title">{m.id}</h1>
      {seriesOf && (
        <p className="model__series">
          a release of <a href={`/models/${seriesOf.slug}/`}>{seriesOf.name}</a>
          {seriesOf.verb && (
            <>
              {" · "}
              <a href={`/models/${seriesOf.slug}/#instrument`}>{seriesOf.verb}</a>
            </>
          )}
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
