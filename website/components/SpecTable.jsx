import { researcherName } from "../lib/content";

// checkpoint is an HF resolve URL (…/sup-computer/<id>/resolve/main/ckpt.pt);
// link the repo page, not the raw file
const hfRepoOf = (m) => m.artifacts?.checkpoint?.replace(/\/resolve\/.*$/, "");

// The registry facts for one release. On a series page the first row names
// (and links) the release the specs belong to; on the release page itself
// it names the series instead.
export default function SpecTable({ m, showRelease }) {
  const hfRepo = hfRepoOf(m);
  return (
    <table className="spec-table">
      <tbody>
        {showRelease ? (
          <tr>
            <th>Release</th>
            <td>
              <a href={`/models/${m.id}/`}>{m.id}</a>
            </td>
          </tr>
        ) : (
          <tr><th>Series</th><td>{m.project}</td></tr>
        )}
        <tr><th>Version</th><td>{m.version}</td></tr>
        <tr><th>Git tag</th><td>{m.git_tag}</td></tr>
        <tr><th>Architecture</th><td>{m.architecture}</td></tr>
        <tr><th>Tokenizer</th><td>{`${m.tokenizer.type} (${m.tokenizer.vocab_size})`}</td></tr>
        <tr><th>Parameters</th><td>{m.params.toLocaleString("en-US")}</td></tr>
        <tr><th>Held-out BPC</th><td>{m.held_out_bpc != null ? m.held_out_bpc : "—"}</td></tr>
        <tr>
          <th>Weights</th>
          <td>
            {hfRepo ? (
              <a href={hfRepo}>{hfRepo.replace("https://huggingface.co/", "")} (Hugging Face)</a>
            ) : (
              "—"
            )}
          </td>
        </tr>
        <tr><th>Researcher</th><td>{m.researcher ? researcherName(m.researcher) : "—"}</td></tr>
      </tbody>
    </table>
  );
}
