import { notFound } from "next/navigation";
import { getSeries, getSeriesByProject } from "../../lib/content";
import SeriesPage from "../../components/SeriesPage";

// /<project>/ — the series page, at the root (ADR-0035). The slug is the
// project name (glyph, daydream, pona…), the shortest handle a series has and
// the one the repo uses for projects/<name>/. The static routes (research,
// train, models) win over this segment, and the integrity check refuses a
// project named after one of them. Only the projects in registry.json are
// exported, so any other slug is a 404 on the static host. (No dynamicParams
// override: with output: export, Next treats the generated list as the whole
// route, and setting it false trips the dev server's export check.)

export function generateStaticParams() {
  return getSeries().map((s) => ({ series: s.project }));
}

export function generateMetadata({ params }) {
  const s = getSeriesByProject(params.series);
  if (!s) return {};
  return {
    title: s.name,
    description: s.tagline,
    openGraph: { title: s.name, description: s.tagline, url: `/${s.project}/` },
  };
}

export default function Page({ params }) {
  const s = getSeriesByProject(params.series);
  if (!s) return notFound();
  return <SeriesPage series={s} />;
}
