import { monthYear, researcherName, reportTier } from "../lib/content";

// One report row — title, meta line, summary — shared by the home page, the
// research page, and a series page's lab-notes shelf.
export function ReportItem({ report, pinned = false }) {
  const { frontmatter: fm, slug } = report;
  const tier = reportTier(report);
  return (
    <div className="post-list__item">
      <a className="post-list__link" href={`/research/${slug}/`}>
        {fm.title || slug}
      </a>
      <p className="post-list__meta">
        {pinned && (
          <>
            <span className="tag tag--pinned">pinned</span>{" "}
          </>
        )}
        <span className="tag">{tier === "essay" ? "essay" : fm.type || "lab note"}</span>{" "}
        {[monthYear(fm.date), fm.researcher && `researcher: ${researcherName(fm.researcher)}`]
          .filter(Boolean)
          .join(" · ")}
      </p>
      <p className="post-list__summary">{fm.summary}</p>
    </div>
  );
}

export default function ReportList({ reports, pinnedSlug }) {
  return (
    <div className="post-list">
      {reports.map((r) => (
        <ReportItem key={r.slug} report={r} pinned={r.slug === pinnedSlug} />
      ))}
    </div>
  );
}
