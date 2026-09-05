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
  const reports = getReports();
  const selected = SELECTED.map((slug) => reports.find((r) => r.slug === slug)).filter(Boolean);
  const series = getSeries();

  return (
    <>
      <h1 className="sr-only">sup computer — a small language model studio</h1>
      <div className="intro">
        <p>
          sup computer is a research studio building small language models from
          scratch — small enough to train end to end on a consumer laptop, and still
          useful.
        </p>
        <p>
          Our methods are LLM-assisted. A mixture of models works each step, from dataset
          creation to training and evaluation, under human direction. All of our research is open source.
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
        <a href="/research/">read more research</a>
      </p>
    </>
  );
}
