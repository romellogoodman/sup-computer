"""
Persist readable samples from a trained gatsby-nanogpt checkpoint (core + BPE) to
a markdown file, so a run's qualitative behaviour is on the record (not just the
dial counts in eval_dial.py). Writes two sections to runs/<tag>-samples.md:

  1. DIAL — one sample per (level, topic) across a few topics, so you can eyeball
     how the green=N knob changes the text.
  2. TOPIC-HONORING — one story per held-out topic at a fixed low level, the
     open failure of gatsby-nanogpt-2 ("a robot" -> a rabbit, "a clock" -> a
     cloud). Read these and judge whether the story is actually about the topic;
     this is the headline of the BPE-migration round (docs/adr/0023).

Run from the repo root, tokenizers provided ad hoc:
    uv run --with tokenizers python projects/gatsby/generate_samples.py \
        --out_dir projects/gatsby/runs/migrate-bpe-r1 --tag migrate-bpe-r1
"""
import argparse
import os

from _runtime import generate, load_model_and_tokenizer, pick_device
from generate import build_prime  # single source of truth for the control-line prime

HERE = os.path.dirname(os.path.abspath(__file__))

# Dial topics (few, walked across all 5 levels).
DIAL_TOPICS = [
    "a robot who wanted a friend",
    "a clock that lost its tick",
    "a snail racing a beetle",
    "two bakers and a burnt pie",
]

# Held-out topic-honoring set: concrete subjects, easy to judge "is the story
# actually about this?" Includes v2's documented failures (robot, clock).
HELDOUT_TOPICS = [
    "a robot who wanted a friend",
    "a clock that lost its tick",
    "a dragon who was afraid of fire",
    "a submarine exploring the deep sea",
    "a cactus in the desert",
    "a train that could not stop",
    "a violin that played by itself",
    "a spider spinning a web",
    "a lighthouse keeper at night",
    "a kite stuck in a tree",
    "a penguin learning to swim",
    "a wizard who lost his hat",
    "a bicycle race down a hill",
    "a volcano that woke up",
    "a mermaid and a lost pearl",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", default=os.path.join(HERE, "runs", "migrate-bpe-r1"))
    ap.add_argument("--data_dir", default=os.path.join(HERE, "data"))
    ap.add_argument("--tag", default="migrate-bpe-r1", help="run tag -> runs/<tag>-samples.md")
    ap.add_argument("--tokens", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--topic_level", type=int, default=2, help="green level for the topic-honoring set")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--top_k", type=int, default=200)
    ap.add_argument("--device", default=None)
    a = ap.parse_args()

    device = pick_device(a.device)
    model, tok = load_model_and_tokenizer(a.out_dir, a.data_dir, device)

    def gen(prime, seed):
        return generate(model, tok, prime, a.tokens, device, seed=seed,
                        temperature=a.temperature, top_k=a.top_k)

    lines = [f"# Sample dump — `{a.tag}` (core engine, byte-level BPE)\n"]
    lines.append(
        f"Raw generations from the `{a.tag}` checkpoint (gatsby on the shared "
        f"`core` engine with byte-level BPE — docs/adr/0023). "
        f"tokens={a.tokens}, temperature={a.temperature}, top_k={a.top_k}, "
        f"seed={a.seed}.\n"
    )

    lines.append("\n## 1. The dial (green=N walked across levels, fixed seed)\n")
    for topic in DIAL_TOPICS:
        lines.append(f"\n### topic: {topic}\n")
        for level in range(1, 6):
            text = gen(build_prime(topic, level), a.seed)
            lines.append(f"\n**green={level}**\n\n```\n{text.strip()}\n```\n")

    lines.append(f"\n## 2. Topic-honoring (held-out topics @ green={a.topic_level})\n")
    lines.append(
        "Judge each: is the story actually about the requested topic? "
        "(v2's failures: a robot -> a rabbit, a clock -> a cloud.)\n"
    )
    for i, topic in enumerate(HELDOUT_TOPICS):
        text = gen(build_prime(topic, a.topic_level), a.seed + i)
        lines.append(f"\n### topic: {topic}\n\n```\n{text.strip()}\n```\n")

    out_path = os.path.join(HERE, "runs", f"{a.tag}-samples.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(lines))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
