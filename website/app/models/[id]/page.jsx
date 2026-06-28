import { notFound } from "next/navigation";
import { getRegistry, getCard, stripLeadIn } from "../../../lib/content";
import Markdown from "../../../components/Markdown";

export function generateStaticParams() {
  return getRegistry().models.map((m) => ({ id: m.id }));
}

export default function Model({ params }) {
  const m = getRegistry().models.find((x) => x.id === params.id);
  if (!m) return notFound();

  const card = getCard(m.id);

  return (
    <>
      <h1>{m.id}</h1>
      <table>
        <tbody>
          <tr><th>Series</th><td>{m.project}</td></tr>
          <tr><th>Version</th><td>{m.version}</td></tr>
          <tr><th>Git tag</th><td>{m.git_tag}</td></tr>
          <tr><th>Architecture</th><td>{m.architecture}</td></tr>
          <tr><th>Tokenizer</th><td>{`${m.tokenizer.type} (${m.tokenizer.vocab_size})`}</td></tr>
          <tr><th>Parameters</th><td>{m.params.toLocaleString("en-US")}</td></tr>
          <tr><th>Held-out BPC</th><td>{m.held_out_bpc != null ? m.held_out_bpc : "—"}</td></tr>
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
