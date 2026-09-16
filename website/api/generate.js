// POST /api/generate — run a released model on a prompt.
//
//   body: { model, prompt?, temp?, topk?, tokens?, seed?, stream? }
//
// `model` is anything `sup` would greet: a release id, a series name, a
// prefix of one, or a greeting alias (kenosha-kid, daydream-micro). The
// prompt defaults to the release's demo prompt. Streaming (the default) is
// server-sent events — one `{"token": "…"}` per decoded piece, then
// `{"done": true, "model", "prompt", "text", "tokens", "truncated"}`;
// `stream: false` returns that final object as one JSON body. `truncated`
// is true when the per-request wall-clock budget ended the run early.
// See ADR-0036.

import { resolve, readOptions, run, validNames } from "../lib/inference.js";
import { route, json, CORS } from "../lib/http.js";

const sse = (obj) => `data: ${JSON.stringify(obj)}\n\n`;

async function handle(request) {
  const startedAt = Date.now();
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "body must be JSON" }, 400);
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return json({ error: "body must be a JSON object" }, 400);
  }
  if (typeof body.model !== "string" || !body.model) {
    return json({ error: "model is required — a release id, a series, or a prefix", valid: validNames() }, 400);
  }

  let model;
  try {
    model = resolve(body.model.trim());
  } catch (err) {
    const status = err.code === "ambiguous" ? 400 : 404;
    return json({ error: err.message, valid: validNames() }, status);
  }

  let opts;
  try {
    opts = readOptions(body);
  } catch (err) {
    return json({ error: err.message }, err.status ?? 400);
  }

  const prompt = opts.prompt ?? model.demo?.prompt;
  if (!prompt) {
    return json({ error: `${model.id} has no demo prompt — send one` }, 400);
  }
  const summary = ({ text, tokens, truncated }) => ({
    done: true,
    model: model.id,
    prompt,
    text,
    tokens,
    truncated,
    temp: opts.temp,
    topk: opts.topk,
    ...(opts.seed !== undefined && { seed: opts.seed }),
  });

  if (!opts.stream) {
    const result = await run(model, { ...opts, prompt, startedAt });
    const { done: _done, ...out } = summary(result);
    return json(out);
  }

  const encoder = new TextEncoder();
  let cancelled = false;
  const stream = new ReadableStream({
    async start(controller) {
      const send = (obj) => controller.enqueue(encoder.encode(sse(obj)));
      try {
        const result = await run(model, {
          ...opts,
          prompt,
          startedAt,
          onToken: (piece) => send({ token: piece }),
          shouldStop: () => cancelled,
        });
        send(summary(result));
      } catch (err) {
        console.error("api/generate:", err?.stack ?? err);
        send({ error: "generation failed" });
      } finally {
        controller.close();
      }
    },
    cancel() {
      cancelled = true;
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      "X-Accel-Buffering": "no",
      ...CORS,
    },
  });
}

export default route({ POST: handle });
