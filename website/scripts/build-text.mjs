// Emit LLM-readable plain-markdown of the research, served as static files.
//
// The site is a static export (no server), so there's no request-time endpoint to
// transform content on the fly. Instead this writes clean .md alongside the HTML so
// any page URL has a raw twin you can paste into an LLM:
//
//   /research/<slug>.md   one report           (page: /research/<slug>/)
//   /models/<id>.md       one model card       (page: /models/<id>/)
//   /llms.txt             index of all of it   (the "start here" URL)
//   /llms-full.txt        every report + card concatenated (one paste = everything)
//
// Files land in public/ (Next copies them verbatim into out/). Runs after
// sync-content (it reads the synced content/ via lib/content.js), wired into the
// predev/prebuild npm hooks. See docs/adr/0019-llm-readable-markdown-endpoints.md.

import { writeFile, rm, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import {
  SITE_URL,
  getReports,
  getCards,
  getRegistry,
  stripLeadIn,
  monthYear,
  researcherName,
} from "../lib/content.js";

const here = dirname(fileURLToPath(import.meta.url));
const pub = resolve(here, "..", "public");

// Charts are light/dark PNG pairs an LLM can't see; the alt text is the content.
// Replace each <picture> block with its alt as a one-line figure note.
const flattenPictures = (s) =>
  s.replace(/<picture[\s\S]*?<\/picture>/g, (block) => {
    const alt = block.match(/alt="([^"]*)"/);
    return alt && alt[1] ? `_Figure: ${alt[1]}_` : "";
  });

// lib/content already rewrote in-repo links/images to root-relative site paths
// (/research/…, /models/…, /research-assets/…). Make them absolute so references
// still resolve once the markdown is pasted out of context.
const absolutize = (s) => s.replace(/(\]\()(\/[^)\s]*)/g, `$1${SITE_URL}$2`);

const clean = (body) => absolutize(flattenPictures(body)).trim();

function reportDoc(r) {
  const fm = r.frontmatter;
  const meta = [
    fm.type,
    monthYear(fm.date),
    fm.series && `series: ${fm.series}`,
    fm.researcher && `researcher: ${researcherName(fm.researcher)}`,
    fm.models?.length && `models: ${fm.models.join(", ")}`,
  ]
    .filter(Boolean)
    .join(" · ");

  return [
    `# ${fm.title}`,
    fm.summary ? `\n> ${fm.summary}` : "",
    `\n${meta}`,
    `\nCanonical: ${SITE_URL}/research/${r.slug}/`,
    `\n---\n`,
    clean(stripLeadIn(r.body)),
    "",
  ].join("\n");
}

// Model cards are already self-contained (H1, **Researcher:**, a spec table), so
// serve the body as-is and just footer a canonical link back to the HTML page.
function cardDoc(card) {
  return [clean(card.body), "", "---", `Canonical: ${SITE_URL}/models/${card.slug}/`, ""].join("\n");
}

const SITE_BLURB =
  "A small language model studio: train small GPTs, write up the research, and show the results.";

function llmsIndex(reports, cards, models) {
  const byId = new Map(models.map((m) => [m.id, m]));
  const research = reports
    .map((r) => `- [${r.frontmatter.title}](${SITE_URL}/research/${r.slug}.md): ${r.frontmatter.summary || ""}`.trimEnd())
    .join("\n");
  const modelList = cards
    .map((c) => {
      const m = byId.get(c.slug);
      const note = m ? `${m.project} char-level GPT, ${m.params?.toLocaleString?.() ?? m.params} params` : "";
      return `- [${c.slug}](${SITE_URL}/models/${c.slug}.md): ${note}`.trimEnd();
    })
    .join("\n");

  return [
    "# sup computer",
    `\n> ${SITE_BLURB}`,
    "\nThese links point at raw markdown — paste any of them into an LLM chat.",
    "\n## Research",
    `\n${research}`,
    "\n## Models",
    `\n${modelList}`,
    "",
  ].join("\n");
}

const reports = getReports();
const cards = getCards();
const { models = [] } = getRegistry();

const reportDocs = reports.map((r) => ({ path: `research/${r.slug}.md`, text: reportDoc(r) }));
const cardDocs = cards.map((c) => ({ path: `models/${c.slug}.md`, text: cardDoc(c) }));

const full = [
  "# sup computer — full research corpus",
  `\n> ${SITE_BLURB}`,
  ...reportDocs.map((d) => `\n---\n\n${d.text}`),
  ...cardDocs.map((d) => `\n---\n\n${d.text}`),
  "",
].join("\n");

// Clean the generated trees so a removed report/model doesn't leave a stale .md.
await rm(resolve(pub, "research"), { recursive: true, force: true });
await rm(resolve(pub, "models"), { recursive: true, force: true });
await mkdir(resolve(pub, "research"), { recursive: true });
await mkdir(resolve(pub, "models"), { recursive: true });

for (const d of [...reportDocs, ...cardDocs]) {
  await writeFile(resolve(pub, d.path), d.text);
}
await writeFile(resolve(pub, "llms.txt"), llmsIndex(reports, cards, models));
await writeFile(resolve(pub, "llms-full.txt"), full);

console.log(
  `wrote ${reportDocs.length} report + ${cardDocs.length} model .md, llms.txt, llms-full.txt -> public/`
);
