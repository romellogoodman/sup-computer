"use client";

// The raw view: prompt (faint) + everything the model emitted, verbatim.
// Every instrument keeps this one toggle away — a view is an interpretation
// of this stream, never a different source.

export default function TokenPane({ prompt, output, busy, placeholder }) {
  const started = Boolean(output) || busy;
  return (
    <pre className="instrument__output" aria-live="polite">
      {prompt && started ? <span className="instrument__output-prompt">{prompt}</span> : null}
      {output || (busy ? "" : placeholder ?? "output appears here — the model runs entirely in your browser.")}
      {busy && <span className="instrument__cursor">▮</span>}
    </pre>
  );
}
