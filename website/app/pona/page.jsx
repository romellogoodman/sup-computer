import { getRegistry } from "../../lib/content";
import PonaChat from "../../components/PonaChat";

export const metadata = {
  title: "pona",
  description:
    "Talk with pona — a word-level Toki Pona GPT whose entire vocabulary is the keyboard.",
  openGraph: {
    title: "pona",
    description:
      "Talk with pona — a word-level Toki Pona GPT whose entire vocabulary is the keyboard.",
    url: "/pona/",
  },
};

export default function PonaPage() {
  const registry = getRegistry();
  return (
    <>
      <h1 className="pona__title">pona</h1>
      <p className="pona__lede">
        pona is a GPT learning to actually speak a language: Toki Pona — about 130
        words, 14 letters, no inflection — is small enough that a studio-scale model
        can get it <em>right</em>, and &ldquo;right&rdquo; is machine-checked by a
        real grammar checker. The model is word-level, so its ~368-token vocabulary{" "}
        <em>is</em> the keyboard below: every word it knows is a key, and as you
        compose, the suggestion strip shows the five words it expects next. It
        speaks as <strong>ilo</strong>.
      </p>
      <PonaChat models={registry.models} />
    </>
  );
}
