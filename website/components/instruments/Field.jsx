"use client";

// Small form furniture every instrument shares: labelled number and range
// inputs, the run/stop button, and the cautionary notice.

export function NumberField({ label, value, onChange, min, max, step = 1, disabled, id }) {
  return (
    <label className="instrument__field">
      <span className="instrument__label">{label}</span>
      <input
        id={id}
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={disabled}
      />
    </label>
  );
}

export function RangeField({ label, value, onChange, min, max, step = 1, disabled, format, id, ticks }) {
  return (
    <label className="instrument__field instrument__field--range">
      <span className="instrument__label">
        {label}
        <span className="instrument__value">{format ? format(value) : value}</span>
      </span>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={disabled}
        list={ticks ? `${id}-ticks` : undefined}
      />
      {ticks && (
        <datalist id={`${id}-ticks`}>
          {ticks.map((t) => (
            <option key={t} value={t} />
          ))}
        </datalist>
      )}
    </label>
  );
}

export function TextField({ label, value, onChange, disabled, id, placeholder, maxLength }) {
  return (
    <label className="instrument__field instrument__field--text">
      <span className="instrument__label">{label}</span>
      <input
        id={id}
        type="text"
        value={value}
        placeholder={placeholder}
        maxLength={maxLength}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        autoComplete="off"
        spellCheck={false}
      />
    </label>
  );
}

export function RunButton({ generating, loading, disabled, onRun, onStop, label = "generate" }) {
  if (generating) {
    return (
      <button type="button" className="instrument__button" onClick={onStop}>
        stop
      </button>
    );
  }
  return (
    <button type="button" className="instrument__button" onClick={onRun} disabled={disabled || loading}>
      {loading ? "loading model…" : label}
    </button>
  );
}

export function Notice({ children }) {
  return <p className="instrument__notice">{children}</p>;
}

/** One line of provenance under the strip: where the compute is happening. */
export function BackendLine({ state, backend, model, extra }) {
  const where =
    state === "ready" || state === "generating"
      ? `runs in your browser on ${backend === "webgpu" ? "WebGPU" : "WebAssembly"}`
      : state === "loading"
        ? "downloading the model to your browser…"
        : state === "failed"
          ? "the model failed to load"
          : "the model downloads on first use and runs entirely in your browser";
  return (
    <p className="instrument__backend">
      {model?.id ? <a href={`/models/${model.id}/`}>{model.id}</a> : null}
      {model?.id ? " · " : ""}
      {where}
      {extra ? ` · ${extra}` : ""}
    </p>
  );
}
