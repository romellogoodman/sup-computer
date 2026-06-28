import { getRegistry } from "../../lib/content";

export default function Models() {
  const { models } = getRegistry();

  const groups = {};
  for (const m of models) {
    (groups[m.project] ||= []).push(m);
  }

  return (
    <>
      <h1>Models</h1>
      <p className="meta">
        Every released version, scored in bits-per-character on the same held-out test.
      </p>
      {Object.entries(groups).map(([project, series]) => (
        <div key={project}>
          <h3>{project}</h3>
          <table>
            <thead>
              <tr>
                <th>Version</th>
                <th>Architecture</th>
                <th>Tokenizer</th>
                <th>Params</th>
                <th>BPC</th>
              </tr>
            </thead>
            <tbody>
              {series.map((m) => (
                <tr key={m.id}>
                  <td>
                    <a href={"/models/" + m.id + "/"}>{m.id}</a>
                  </td>
                  <td>{m.architecture}</td>
                  <td>{m.tokenizer.type}</td>
                  <td>{m.params.toLocaleString("en-US")}</td>
                  <td>{m.held_out_bpc != null ? m.held_out_bpc : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </>
  );
}
