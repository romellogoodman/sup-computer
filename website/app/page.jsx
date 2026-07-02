import { getReports, getRegistry, monthYear, researcherName } from "../lib/content";

export default function Home() {
  const reports = getReports();
  const { models } = getRegistry();
  const modelsByName = [...models].sort(
    (a, b) => a.project.localeCompare(b.project) || b.version - a.version,
  );

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
          Our methods are LLM-assisted: a mixture of models works each step, from dataset
          creation to training and evaluation, under human direction. All of our research is open-source and freely available.
        </p>
        {/* <p>
          All of our research is open-source and freely available.
        </p> */}
      </div>

      <h2 className="section-label" id="models">Models</h2>
      <ul className="model-list">
        {modelsByName.map((m) => (
          <li className="model-list__item" key={m.id}>
            <a href={"/models/" + m.id + "/"}>{m.id}</a>
            <span className="model-list__spec">
              {m.architecture.split("(")[0].trim()}
              {m.held_out_bpc != null && (
                <>
                  {" · BPC "}
                  <span className="model-list__bpc">{m.held_out_bpc}</span>
                </>
              )}
              {m.params != null && ` · ${(m.params / 1e6).toFixed(1)}M`}
            </span>
          </li>
        ))}
      </ul>

      <h2 className="section-label" id="research">Research</h2>
      {reports.map((r, i) => (
        <div className="post-list__item" key={r.slug}>
          <a className="post-list__link" href={"/research/" + r.slug + "/"}>{r.frontmatter.title || r.slug}</a>
          <p className="post-list__meta">
            {i === 0 && <><span className="tag tag--new">new</span>{" "}</>}
            {r.frontmatter.type && <span className="tag">{r.frontmatter.type}</span>}{" "}
            {[
              monthYear(r.frontmatter.date),
              r.frontmatter.researcher && `researcher: ${researcherName(r.frontmatter.researcher)}`,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          <p className="post-list__summary">{r.frontmatter.summary}</p>
        </div>
      ))}
    </>
  );
}
