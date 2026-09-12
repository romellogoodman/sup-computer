import { getEssays, getLabNotes } from "../../lib/content";
import ReportList from "../../components/ReportList";

export const metadata = {
  title: "research",
  description:
    "Research from sup computer, a small language model studio: essays by its director and lab notes written by the models that ran the experiments.",
  openGraph: {
    title: "research",
    description:
      "Research from sup computer, a small language model studio: essays by its director and lab notes written by the models that ran the experiments.",
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
        Essays are Romello Goodman&apos;s questions. Lab notes are the experiments that chase
        them, written by the model that ran each one.
      </p>

      <h2 className="section-label" id="essays">Essays</h2>
      <ReportList reports={essays} showType={false} />

      <h2 className="section-label" id="lab-notes">Lab notes</h2>
      <ReportList reports={labNotes} />
    </>
  );
}
