import { getEssays, getLabNotes, getSeries } from "../../lib/content";
import ReportList, { ReportItem } from "../../components/ReportList";

export const metadata = {
  title: "research",
  description:
    "Essays by the studio's director and the lab notes its agents write: every experiment, filed by model.",
  openGraph: {
    title: "research",
    description:
      "Essays by the studio's director and the lab notes its agents write: every experiment, filed by model.",
    url: "/research/",
  },
};

// Lab notes shelve by the `series:` their frontmatter names. Series that are
// model families get their series-page name; studio-level series (core, the
// player) keep their own label.
function shelfName(seriesKey, allSeries) {
  if (!seriesKey) return "studio";
  const s = allSeries.find((x) => x.project === seriesKey || x.project.startsWith(seriesKey));
  return s ? s.name : seriesKey;
}

export default function Research() {
  const essays = getEssays();
  const labNotes = getLabNotes();
  const allSeries = getSeries();

  const shelves = new Map();
  for (const r of labNotes) {
    const key = shelfName(r.frontmatter.series, allSeries);
    if (!shelves.has(key)) shelves.set(key, []);
    shelves.get(key).push(r);
  }
  // newest shelf first (reports are already newest-first within a shelf)
  const ordered = [...shelves.entries()].sort(
    (a, b) => new Date(b[1][0].frontmatter.date) - new Date(a[1][0].frontmatter.date),
  );

  return (
    <>
      <h1 className="report__title">Research</h1>
      <p className="intro">
        Two shelves. Essays are written by Romello Goodman, one per question the studio has
        chased. Lab notes are the experiments behind them, run and written up by Claude models
        under direction, filed under the model they produced.
      </p>

      <h2 className="section-label" id="essays">Essays</h2>
      <ReportList reports={essays} />

      <h2 className="section-label" id="lab-notes">Lab notes</h2>
      {ordered.map(([shelf, reports]) => (
        <div key={shelf}>
          <p className="post-list__group">{shelf}</p>
          {reports.map((r) => (
            <ReportItem key={r.slug} report={r} />
          ))}
        </div>
      ))}
    </>
  );
}
