import { getSeries, getReports } from "../lib/content";
import ReportList from "../components/ReportList";

// Selected research: the reports on the front page, in this order — an
// editorial choice, so it lives here (site presentation), never in a frozen
// report's frontmatter. Any report can be selected, essay or lab note; the
// research page keeps the complete shelves.
const SELECTED = [
  "1-month-and-60-models-later",
  "an-instrument-anything-can-play",
  "budget-cant-buy-the-midgame",
];

export default function Home() {
  const all = getReports();
  const selected = SELECTED.map((slug) => all.find((r) => r.slug === slug)).filter(Boolean);
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
                <a className="model-list__verb" href={`/models/${slug}/`}>
                  {verb}
                </a>
              )}
            </span>
          </li>
        ))}
      </ul>

      <h2 className="section-label" id="research">Selected research</h2>
      <ReportList reports={selected} />
      <p className="post-list__all">
        <a href="/research/">all research, {all.length} reports</a>
      </p>
    </>
  );
}
