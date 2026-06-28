import { getReports } from "../../lib/content";

export default function ResearchIndex() {
  const reports = getReports();
  return (
    <>
      <h1>Research</h1>
      {reports.map((r) => (
        <div className="list-item" key={r.slug}>
          <a href={"/research/" + r.slug + "/"}>{r.frontmatter.title || r.slug}</a>
          <p className="meta">{String(r.frontmatter.date || "")}</p>
          <p>{r.frontmatter.summary}</p>
        </div>
      ))}
    </>
  );
}
