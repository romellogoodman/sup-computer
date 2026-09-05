import { getCard, stripLeadIn, reportsForSeries, reportTier, versionLabel } from "../lib/content";
import Markdown from "./Markdown";
import Instrument from "./instruments/Instrument";
import CardDetails from "./CardDetails";
import SpecTable from "./SpecTable";
import { ReportItem } from "./ReportList";

// One page per model series, at /<project>/ (ADR-0035): the instrument
// first, wired to the newest release per lineage; then specs, the release
// list, the lab notes filed under the series, and the demoted model card
// (open on a wide screen, collapsed on a phone).
export default function SeriesPage({ series }) {
  const { slug, name, tagline, verb, instrument, flagship, versions, latest } = series;
  const card = getCard(flagship.id);
  const filed = reportsForSeries(series);
  const essays = filed.filter((r) => reportTier(r) === "essay");
  const labNotes = filed.filter((r) => reportTier(r) === "lab-note");

  return (
    <>
      <h1 className="series__title">{name}</h1>
      <p className="series__tagline">{tagline}</p>

      <Instrument kind={instrument} series={{ slug, name, tagline, verb }} models={latest} />

      <h2 className="section-label series__section" id="specs">Specs</h2>
      <SpecTable m={flagship} showRelease />
      {latest.length > 1 && (
        <p className="section-note">
          The instrument runs {latest.length} sibling releases:{" "}
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
