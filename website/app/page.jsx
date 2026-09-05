import { getSeries, getEssays, getLabNotes } from "../lib/content";
import ReportList from "../components/ReportList";

// The essay pinned to the top of the research list — an editorial choice, so
// it lives here (site presentation), not in the frozen report's frontmatter.
const PINNED_SLUG = "1-month-and-60-models-later";

export default function Home() {
  const essays = getEssays();
  const reports = [
    ...essays.filter((r) => r.slug === PINNED_SLUG),
    ...essays.filter((r) => r.slug !== PINNED_SLUG),
  ];
  const labNoteCount = getLabNotes().length;
  const series = getSeries();

  return (
    <>
      <h1 className="sr-only">sup computer — a small language model studio</h1>
      <div className="intro">
        <p>
          sup computer trains small language models from scratch and builds each one an
          instrument: a board for the model that dreams chess, a font maker for the one that
          draws letters, a keyboard for the one that speaks Toki Pona. Every model is small
          enough to train end to end on a laptop, and every instrument runs in your browser.
        </p>
        <p>
          The research is LLM-assisted. Claude models run each experiment under human direction
          and sign the lab notes; the essays are by Romello Goodman. All of it is open source.
        </p>
      </div>

      <h2 className="section-label" id="models">Models</h2>
      <ul className="model-list">
        {series.map(({ slug, name, tagline, verb }) => (
          <li className="model-list__item" key={slug}>
            <span className="model-list__name">
              <a href={`/models/${slug}/`}>{name}</a>
              {tagline && <span className="model-list__tagline">{tagline}</span>}
            </span>
            <span className="model-list__spec">
              {verb && (
                <a className="model-list__verb" href={`/models/${slug}/#instrument`}>
                  {verb}
                </a>
              )}
            </span>
          </li>
        ))}
      </ul>

      <h2 className="section-label" id="research">Research</h2>
      <ReportList reports={reports} pinnedSlug={PINNED_SLUG} />
      <p className="section-note">
        The lab notes behind each model — {labNoteCount} experiments and notes run by the
        studio's agents — are filed on the <a href="/research/">research page</a> and under
        each model.
      </p>
    </>
  );
}
