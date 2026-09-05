"use client";

// useModel — React state around one ModelClient for one registry model.
//
//   const m = useModel(model);       // model: a registry.json entry (or null)
//   m.state                          // "cold" | "loading" | "ready" | "failed" | "unpublished"
//   await m.ensure()                 // lazy: the download starts on first use
//   const run = m.generate(opts, onToken); await run.done;   // sets m.generating
//   m.stop()                         // halts the current run
//   m.vocab                          // itos array for char models, else null
//   await m.forward(ids)             // raw logits (Float32Array)
//
// The worker is created on first ensure() and terminated when the model
// changes or the component unmounts, so a switched-away model never keeps
// computing in the background.

import { useCallback, useEffect, useRef, useState } from "react";
import { ModelClient } from "./client";
import { pickBundle } from "./bundle";

export function useModel(model) {
  const clientRef = useRef(null);
  const loadRef = useRef(null); // the in-flight load promise, shared by callers
  const runRef = useRef(null); // the current generate handle
  const [state, setState] = useState(() => (pickBundle(model) ? "cold" : "unpublished"));
  const [error, setError] = useState(null);
  const [vocab, setVocab] = useState(null);
  const [backend, setBackend] = useState(null); // "webgpu" | "wasm" once loaded
  const [generating, setGenerating] = useState(false);

  // Tear down on model change / unmount.
  useEffect(() => {
    setState(pickBundle(model) ? "cold" : "unpublished");
    setError(null);
    setVocab(null);
    setBackend(null);
    setGenerating(false);
    return () => {
      runRef.current = null;
      loadRef.current = null;
      clientRef.current?.terminate();
      clientRef.current = null;
    };
  }, [model?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const ensure = useCallback(async () => {
    if (clientRef.current && loadRef.current) return loadRef.current.then(() => clientRef.current);
    const bundle = pickBundle(model);
    if (!bundle) throw new Error("no published artifacts for this release yet");
    const client = new ModelClient();
    clientRef.current = client;
    setState("loading");
    setError(null);
    loadRef.current = client
      .load(bundle, model.block_size || 256)
      .then(({ vocab: v, webgpu }) => {
        if (clientRef.current !== client) return;
        setVocab(v);
        setBackend(bundle.int8 ? "wasm" : webgpu ? "webgpu" : "wasm");
        setState("ready");
      })
      .catch((e) => {
        if (clientRef.current !== client) return;
        setError(e?.message || String(e));
        setState("failed");
        throw e;
      });
    await loadRef.current;
    return client;
  }, [model]);

  const forward = useCallback(async (ids) => (await ensure()).forward(ids), [ensure]);
  const encode = useCallback(async (text) => (await ensure()).encode(text), [ensure]);
  const decode = useCallback(async (ids) => (await ensure()).decode(ids), [ensure]);

  /**
   * Start a generation; resolves to the worker's { text, ids, stopped }.
   * Only one at a time per model — a second call stops the first.
   */
  const generate = useCallback(
    (opts, onToken) => {
      const handle = { stopped: false, done: null, stop: null };
      handle.done = (async () => {
        const client = await ensure();
        if (runRef.current) runRef.current.stop?.();
        if (handle.stopped) return { text: "", ids: [], stopped: true };
        const run = client.generate(opts, onToken);
        handle.stop = run.stop;
        runRef.current = handle;
        setGenerating(true);
        try {
          return await run.done;
        } finally {
          if (runRef.current === handle) {
            runRef.current = null;
            setGenerating(false);
          }
        }
      })();
      const stop = () => {
        handle.stopped = true;
        handle.stop?.();
      };
      return { done: handle.done, stop };
    },
    [ensure],
  );

  const stop = useCallback(() => {
    runRef.current?.stop?.();
    if (runRef.current) runRef.current.stopped = true;
  }, []);

  return { state, error, vocab, backend, generating, ensure, forward, encode, decode, generate, stop };
}
