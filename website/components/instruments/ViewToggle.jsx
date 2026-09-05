"use client";

// demo / token — the instrument's own rendering, or the raw stream.

export default function ViewToggle({ view, onChange, demoLabel = "demo" }) {
  const tab = (key, label) => (
    <button
      type="button"
      role="tab"
      aria-selected={view === key}
      className={`instrument__mode${view === key ? " instrument__mode--on" : ""}`}
      onClick={() => onChange(key)}
    >
      {label}
    </button>
  );
  return (
    <div className="instrument__modes" role="tablist" aria-label="output view">
      {tab("demo", demoLabel)}
      {tab("token", "token")}
    </div>
  );
}
