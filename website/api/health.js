// GET /api/health — is the function up, and which models this instance
// already holds in memory. Fluid compute shares an instance across
// invocations and scales to zero, so `loaded` is a snapshot, not a promise.

import { loadedIds } from "../lib/inference.js";
import { route, json } from "../lib/http.js";

export default route({
  GET: () => json({ ok: true, loaded: loadedIds() }, 200, { "Cache-Control": "no-store" }),
});
