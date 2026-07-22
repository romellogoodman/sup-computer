import { getReports, getRegistry, monthYear, researcherName } from "../lib/content";

// The report pinned to the top of the research list — an editorial choice, so
// it lives here (site presentation), not in the frozen report's frontmatter.
const PINNED_SLUG = "1-month-and-60-models-later";

export default function Home() {
  const all = getReports();
  const reports = [
    ...all.filter((r) => r.slug === PINNED_SLUG),
    ...all.filter((r) => r.slug !== PINNED_SLUG),
  ];
  const registry = getRegistry();
  const { models } = registry;
  const seriesCopy = registry.series || {};
  // Collapse one-row-per-release into one-row-per-series (grouped by project) —
  // see the model-series-pages design. Each row lists its versions (v1, v2, and
  // variant tiers like v1-micro); series taglines live in registry.json's
  // `series` map. Version chips link to each release page; the series name links
  // to the flagship for now and gets repointed to /models/<slug>/ when series
  // pages ship.
  const versionLabel = (m, slug) => {
    const rest = m.id.startsWith(slug) ? m.id.slice(slug.length) : m.id;
    const variant = rest.replace(/^-/, "").replace(/-?\d+$/, "");
    return variant ? `v${m.version}-${variant}` : `v${m.version}`;
  };
  const byProject = {};
  for (const m of models) (byProject[m.project] ||= []).push(m);
  const series = Object.values(byProject)
    .map((members) => {
      const maxVersion = Math.max(...members.map((m) => m.version));
      // flagship = latest version; among sibling tiers (same version) prefer the
      // base id (shortest slug, e.g. daydream's Regular over micro/grand).
      const flagship = members
        .filter((m) => m.version === maxVersion)
        .sort((a, b) => a.id.length - b.id.length)[0];
      const slug = flagship.id.replace(/-\d+$/, "");
      // latest → oldest; within a version, base tier before its variants
      const versions = [...members].sort(
        (a, b) => b.version - a.version || a.id.length - b.id.length || a.id.localeCompare(b.id),
      );
      return { slug, flagship, tagline: seriesCopy[slug]?.tagline || flagship.tagline, versions };
    })
    .sort((a, b) => a.slug.localeCompare(b.slug));

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
        {series.map(({ slug, flagship, tagline, versions }) => (
          <li className="model-list__item" key={slug}>
            <span className="model-list__name">
              <a href={"/models/" + flagship.id + "/"}>{slug}</a>
              {tagline && <span className="model-list__tagline">{tagline}</span>}
            </span>
            <span className="model-list__spec">
              {versions.map((m, i) => (
                <span key={m.id}>
                  {i > 0 && " · "}
                  <a href={"/models/" + m.id + "/"}>{versionLabel(m, slug)}</a>
                </span>
              ))}
            </span>
          </li>
        ))}
      </ul>


      <h2 className="section-label" id="research">Research</h2>
      {reports.map((r) => (
        <div className="post-list__item" key={r.slug}>
          <a className="post-list__link" href={"/research/" + r.slug + "/"}>{r.frontmatter.title || r.slug}</a>
          <p className="post-list__meta">
            {r.slug === PINNED_SLUG && <><span className="tag tag--pinned">pinned</span>{" "}</>}
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
