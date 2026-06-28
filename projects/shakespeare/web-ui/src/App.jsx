import { useState } from "react";
import "./App.scss";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

function App() {
  const [start, setStart] = useState("ROMEO:");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function generate(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setOutput("");
    try {
      const res = await fetch(`${API_URL}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ start }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Generation failed");
      setOutput(data.output);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app">
      <section className="generator">
        <h1 className="generator__title">Shakespeare GPT</h1>
        <p className="generator__subtitle">
          A 10.6M-parameter character-level model trained from scratch on
          Shakespeare. Type a starting prompt and generate.
        </p>

        <form className="generator__form" onSubmit={generate}>
          <label className="generator__label" htmlFor="start">
            Start prompt
          </label>
          <textarea
            id="start"
            className="generator__input"
            value={start}
            onChange={(event) => setStart(event.target.value)}
            rows={3}
            placeholder="e.g. ROMEO:"
          />
          <button className="generator__button" type="submit" disabled={loading}>
            {loading ? "Generating…" : "Generate"}
          </button>
        </form>

        {error && <p className="generator__error">{error}</p>}
        {output && <pre className="generator__output">{output}</pre>}
      </section>
    </main>
  );
}

export default App;
