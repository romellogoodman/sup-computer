import { notFound } from "next/navigation";
import { getRegistry, getCard, stripLeadIn, researcherName } from "../../../lib/content";
import Markdown from "../../../components/Markdown";

export function generateStaticParams() {
  return getRegistry().models.map((m) => ({ id: m.id }));
}

export function generateMetadata({ params }) {
  const m = getRegistry().models.find((x) => x.id === params.id);
  if (!m) return {};
  const description = `${m.architecture} · ${m.tokenizer.type} tokenizer · ${m.params.toLocaleString("en-US")} parameters`;
  return {
    title: m.id,
    description,
    openGraph: { title: m.id, description, url: `/models/${m.id}/` },
  };
}

export default function Model({ params }) {
  const m = getRegistry().models.find((x) => x.id === params.id);
  if (!m) return notFound();

  const card = getCard(m.id);
  // checkpoint is an HF resolve URL (…/sup-computer/<id>/resolve/main/ckpt.pt);
  // link the repo page, not the raw file
  const hfRepo = m.artifacts?.checkpoint?.replace(/\/resolve\/.*$/, "");

  return (
    <>
      <h1 className="model__title">{m.id}</h1>
      <table className="spec-table">
        <tbody>
          <tr><th>Series</th><td>{m.project}</td></tr>
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
      {card && (
        <>
          <hr />
          <Markdown>{stripLeadIn(card.body)}</Markdown>
        </>
      )}
    </>
  );
}
