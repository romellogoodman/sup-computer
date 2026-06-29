import { getReports, getRegistry, monthYear, researcherName } from "../lib/content";

export default function Home() {
  const reports = getReports();
  const { models } = getRegistry();
  const modelsByName = [...models].sort((a, b) => a.id.localeCompare(b.id));

  return (
    <>
      <div className="intro">
        <p>
          sup computer is a studio for building small language models from scratch —
          training them, writing up what happens, showing the work.
        </p>
        <p>
          Small is the point: a model you can train on a laptop in minutes, read end
          to end, and run in a browser. Small enough to understand completely.
        </p>
        <p>
          It is also a research practice. A Claude model is the researcher — diagnosing
          models, proposing changes, training new versions, measuring them — under
          human direction. Not recursive self-improvement: a person sets the goals and
          keeps oversight; the model implements and tests. Every report and model says
          which researcher did the work — so far, Claude Opus 4.8.
        </p>
        <p>
          Everything is open and one directory away — configs, run logs, model cards,
          charts. This site is the lab notebook.
        </p>
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
