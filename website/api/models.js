// GET /api/models — the greetable roster, the same one `sup list` prints:
// the newest runnable release per lineage, plus every name that resolves.
// See docs/adr/0036-hosted-inference-api.md.

import { roster } from "../lib/inference.js";
import { route, json } from "../lib/http.js";

export default route({
  GET: () => json(roster(), 200, { "Cache-Control": "public, max-age=300" }),
});
