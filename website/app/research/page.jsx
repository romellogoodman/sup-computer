import { getEssays, getLabNotes } from "../../lib/content";
import ReportList from "../../components/ReportList";

export const metadata = {
  title: "research",
  description:
    "Essays by the studio's director and the lab notes its agents write: every experiment, newest first.",
  openGraph: {
    title: "research",
    description:
      "Essays by the studio's director and the lab notes its agents write: every experiment, newest first.",
    url: "/research/",
  },
};

export default function Research() {
  const essays = getEssays();
  // getLabNotes() returns newest first; one list, no shelving by series.
  const labNotes = [...getLabNotes()].sort(
    (a, b) => new Date(b.frontmatter.date) - new Date(a.frontmatter.date),
  );

  return (
    <>
      <h1 className="report__title">Research</h1>
      <p className="intro">
        Two shelves. Essays are written by Romello Goodman, one per question the studio has
        chased. Lab notes are the experiments behind them, run and written up by Claude models
        under direction, newest first.
      </p>

      <h2 className="section-label" id="essays">Essays</h2>
      <ReportList reports={essays} showType={false} />

      <h2 className="section-label" id="lab-notes">Lab notes</h2>
      <ReportList reports={labNotes} />
    </>
  );
}
