"use client";

// The generic text instrument: a prompt, the sampling knobs, run/stop, a
// per-series demo view with the raw token pane one toggle away, and the
// next-token strip underneath. The three prose instruments (playbill, chant,
// greenlight) are thin wrappers that supply a View, their own controls, and
// how the prompt is built; a series with no instrument of its own gets this
// component bare.
//
// Props:
//   model           registry entry to run
//   prompt          the prompt string (controlled by the parent)
//   onPromptChange  editable prompt textarea when given; hidden otherwise
//   View            demo renderer ({ prompt, output, busy, model }) — optional
//   controls        render prop ({ disabled }) placed above the generic knobs
//   fields          which generic knobs to show: ["temp","topk","max"] (default all)
//   defaults        { temp, topk, maxNewTokens }
//   stopAt          token ids that end a run
//   placeholder     token-pane text before the first run

import { useEffect, useRef, useState } from "react";
import { useModel } from "../../lib/instrument/useModel";
import DistributionStrip from "./DistributionStrip";
import TokenPane from "./TokenPane";
import ViewToggle from "./ViewToggle";
import { NumberField, RunButton, Notice, BackendLine } from "./Field";

const ALL_FIELDS = ["temp", "topk", "max"];

export default function TextInstrument({
  model,
  prompt,
  onPromptChange,
  View,
  controls,
  fields = ALL_FIELDS,
  defaults = {},
  stopAt,
  placeholder,
  runLabel,
  topN = 8,
  demoLabel,
  onState,
}) {
  const m = useModel(model);
  const [temp, setTemp] = useState(defaults.temp ?? 0.8);
  const [topk, setTopk] = useState(defaults.topk ?? 40);
  const [maxNewTokens, setMaxNewTokens] = useState(defaults.maxNewTokens ?? 200);
  const [output, setOutput] = useState("");
  const [top, setTop] = useState(null);
  const [view, setView] = useState(View ? "demo" : "token");
  const [runError, setRunError] = useState(null);
  const handleRef = useRef(null);

  const busy = m.state === "loading" || m.generating;
  const runnable = m.state !== "unpublished" && m.state !== "failed";

  // Let a parent react to sampler state (e.g. sync a dial) without owning it.
  useEffect(() => {
    onState?.({ temp, topk, maxNewTokens, busy, state: m.state, backend: m.backend });
  }, [temp, topk, maxNewTokens, busy, m.state, m.backend, onState]);

  // Parent-driven knobs (a dial that sets temperature) come in via defaults.
  useEffect(() => {
    if (defaults.temp !== undefined) setTemp(defaults.temp);
  }, [defaults.temp]);
  useEffect(() => {
    if (defaults.maxNewTokens !== undefined) setMaxNewTokens(defaults.maxNewTokens);
  }, [defaults.maxNewTokens]);

  const run = async () => {
    if (!runnable || busy) return;
    setOutput("");
    setTop(null);
    setRunError(null);
    const handle = m.generate({ prompt, maxNewTokens, temp, topk, topN, stopAt }, (ev) => {
      if (ev.piece) setOutput((s) => s + ev.piece);
      if (ev.top) setTop(ev.top);
    });
    handleRef.current = handle;
    try {
      await handle.done;
    } catch (e) {
      setRunError(e?.message || String(e));
    }
  };

  const stop = () => handleRef.current?.stop();

  const disabled = !runnable || busy;

  return (
    <div className="instrument">
      {m.state === "unpublished" && (
        <Notice>
          weights not yet published for this release. The instrument lights up the moment
          they land; everything else is already wired.
        </Notice>
      )}
      {m.state === "failed" && <Notice>the model failed to load: {m.error}</Notice>}

      {controls?.({ disabled })}

      {onPromptChange && (
        <>
          <label className="instrument__label" htmlFor={`prompt-${model?.id}`}>
            prompt
          </label>
          <textarea
            id={`prompt-${model?.id}`}
            className="instrument__prompt"
            rows={3}
            value={prompt}
            onChange={(e) => onPromptChange(e.target.value)}
            disabled={disabled}
          />
        </>
      )}

      <div className="instrument__controls">
        {fields.includes("temp") && (
          <NumberField label="temp" value={temp} onChange={setTemp} min={0.1} max={2} step={0.1} disabled={disabled} />
        )}
        {fields.includes("topk") && (
          <NumberField label="top-k" value={topk} onChange={setTopk} min={0} max={200} disabled={disabled} />
        )}
        {fields.includes("max") && (
          <NumberField label="max tokens" value={maxNewTokens} onChange={setMaxNewTokens} min={1} max={4000} disabled={disabled} />
        )}
        <RunButton
          generating={m.generating}
          loading={m.state === "loading"}
          disabled={!runnable}
          onRun={run}
          onStop={stop}
          label={runLabel}
        />
      </div>

      {runError && <p className="instrument__error">error: {runError}</p>}

      {View && <ViewToggle view={view} onChange={setView} demoLabel={demoLabel} />}
      {View && view === "demo" ? (
        <View prompt={prompt} output={output} busy={busy} model={model} />
      ) : (
        <TokenPane prompt={prompt} output={output} busy={busy} placeholder={placeholder} />
      )}

      <DistributionStrip top={top} />
      <BackendLine state={m.state} backend={m.backend} model={model} />
    </div>
  );
}
