import { getReports, getRegistry } from "../lib/content";

export default function Home() {
  const reports = getReports();
  const { models } = getRegistry();

  return (
    <>
      <p>
        sup computer is a studio for building small language models from scratch —
        training them, writing up what happens, and showing the work.
      </p>
      <p>
        Small is the point. A model you can train on a laptop in minutes, read end
        to end, and run in a browser. Small enough to understand completely.
      </p>
      <p>
        It is also a research practice. Claude Opus acts as the researcher —
        diagnosing a model, proposing changes, training new versions, and measuring
        them — under human direction. Not recursive self-improvement: a person sets
        the goals and keeps oversight; the model implements, tests, and measures.
      </p>
      <p>
        Everything is open and one directory away: the configs, the run logs, the
        model cards, the charts. This site is the lab notebook.
      </p>

      <hr />
      <h2>Research</h2>
      {reports.map((r) => (
        <div className="list-item" key={r.slug}>
          <a href={"/research/" + r.slug + "/"}>{r.frontmatter.title || r.slug}</a>
          <p className="meta">
            {[r.frontmatter.type, String(r.frontmatter.date || "")].filter(Boolean).join(" · ")}
          </p>
          <p>{r.frontmatter.summary}</p>
        </div>
      ))}

      <h2>Models</h2>
      <ul>
        {models.map((m) => (
          <li key={m.id}>
            <a href={"/models/" + m.id + "/"}>{m.id}</a>
            {" — " + m.architecture + (m.held_out_bpc != null ? `, BPC ${m.held_out_bpc}` : "")}
          </li>
        ))}
      </ul>
    </>
  );
}
