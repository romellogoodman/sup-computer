import { getRegistry } from "../../lib/content";
import ModelPlayer from "../../components/ModelPlayer";

export const metadata = {
  title: "interfaces",
  description:
    "Run the studio's small models in your browser — pick a release, give it a prompt, watch it generate.",
  openGraph: {
    title: "interfaces",
    description:
      "Run the studio's small models in your browser — pick a release, give it a prompt, watch it generate.",
    url: "/interfaces/",
  },
};

export default function ModelPlayerPage() {
  const registry = getRegistry();
  return (
    <>
      {/* no visible page header by design — the demo is the page */}
      <h1 className="sr-only">interfaces</h1>
      <ModelPlayer models={registry.models} series={registry.series || {}} />
    </>
  );
}
