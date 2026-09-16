// Response helpers shared by the API functions (ADR-0036). Public and
// read-only: CORS is wide open, and every reply carries the same headers.

export const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "86400",
};

export function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...CORS, ...headers },
  });
}

export function preflight() {
  return new Response(null, { status: 204, headers: CORS });
}

export function methodNotAllowed(allow) {
  return json({ error: `method not allowed — use ${allow}` }, 405, { Allow: allow });
}

/** Route on method: `handlers` maps METHOD -> (request) => Response. */
export function route(handlers) {
  const allow = Object.keys(handlers).join(", ");
  return {
    async fetch(request) {
      if (request.method === "OPTIONS") return preflight();
      const handler = handlers[request.method];
      if (!handler) return methodNotAllowed(allow);
      try {
        return await handler(request);
      } catch (err) {
        const status = err?.status ?? 500;
        if (status >= 500) console.error("api:", err?.stack ?? err);
        return json({ error: status >= 500 ? "internal error" : err.message }, status);
      }
    },
  };
}
