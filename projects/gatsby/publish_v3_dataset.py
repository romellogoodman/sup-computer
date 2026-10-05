"""
Stage and publish tiny-green-light-stories v3 to Hugging Face (ADR-0040).

Builds data/v3/hf/ from the generator's outputs, then uploads it to the dataset
repo `sup-computer/tiny-green-light-stories` and tags the revision `v3`:

    README.md                 the dataset card (written here from the manifest)
    v3/train.jsonl            one story per line, split by topic
    v3/validation.jsonl
    v3/test.jsonl
    v3/manifest.json          the generation record: prompts, params, counts, cost
    v3/topics.json            the topic bank with each topic's sampled details
    v3/subsets/train-*.json   the declared training subsets (topic-id lists)

v1 and v2 join the same repo as configs once their generators' output terms are
checked (ADR-0040); the card says so.

Run from the repo root:
    uv run python projects/gatsby/publish_v3_dataset.py            # stage only
    uv run python projects/gatsby/publish_v3_dataset.py --upload   # stage + push
"""
import argparse
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.join(HERE, "data", "v3")
STAGE = os.path.join(V3, "hf")
REPO = "sup-computer/tiny-green-light-stories"
SPLITS = {"train": "train", "val": "validation", "test": "test"}


def row_out(r):
    d = dict(r["details"])
    d["wording"] = "".join(map(str, d["wording"]))   # [0, 1, "a"] -> "01a" (one Arrow type)
    keep = ("id", "topic_id", "level", "obsession", "topic", "theme", "subtheme", "name",
            "text", "greens", "writer")
    return {**{k: r[k] for k in keep}, "details": d}


def card(m, stats, counts, n_topics, rows):
    c = m["cost_usd"]
    l1_hot = sum(r["level"] == 1 and r["greens"] > 3 for r in rows)
    l1_n = sum(r["level"] == 1 for r in rows)
    no_name = sum(r["name"] not in r["text"] for r in rows)
    sub = "\n".join(f"| `subsets/train-{k}.json` | {v['topics']:,} | {v['stories']:,} | {v['tokens']:,} |"
                    for k, v in stats.items() if k in ("5k", "10k", "full"))
    return f"""---
license: mit
language:
  - en
pretty_name: tiny green light stories
size_categories:
  - 10K<n<100K
task_categories:
  - text-generation
tags:
  - synthetic
  - tinystories
  - children-stories
  - controllable-generation
configs:
  - config_name: v3
    default: true
    data_files:
      - split: train
        path: v3/train.jsonl
      - split: validation
        path: v3/validation.jsonl
      - split: test
        path: v3/test.jsonl
---

# tiny green light stories

> A [sup computer](https://www.supcpu.com) dataset. Trains [`gatsby-nanogpt-3`](https://huggingface.co/sup-computer/gatsby-nanogpt-3) · [monorepo](https://github.com/romellogoodman/sup-computer) (generator: [`projects/gatsby/generate_v3.py`](https://github.com/romellogoodman/sup-computer/blob/main/projects/gatsby/generate_v3.py)).

Children's stories in the TinyStories register, each secretly obsessed with a
green light, at a labelled intensity from 1 to 5. At level 1 the light shows up
once or twice at the edge of the story; at level 5 it swallows the story after
a sentence or two. Every topic is written at all five levels, so within a topic
only the obsession changes.

## Versions

Each version is its own corpus with its own writer. **v3 is not a superset of
v1 or v2**; the numbers order the corpora, they don't nest.

| version | stories | writer | status |
|---|---|---|---|
| v1 | 1,000 | Claude Sonnet 4.6 | trains gatsby-nanogpt-1; not yet published here |
| v2 | 2,000 | Olmo 3 7B, Ministral 3 8B, Gemma 4 26B, Granite 4.1 8B | trains gatsby-nanogpt-2; not yet published here |
| **v3** | **{m['stories']:,}** | **DeepSeek V4.1 Flash** | **this release** |

v1 and v2 will join as configs once their writers' output terms are checked.

## v3 at a glance

- **{m['stories']:,} stories** over {n_topics:,} topics × 5 levels (one story never came back), written by
  `{m['writer']}` via OpenRouter on {m['generated_at'][:10]}.
- **Split by topic**: train {counts['train']:,} / validation {counts['val']:,} /
  test {counts['test']:,}. No test topic appears in train or validation.
- **Cost**: ${c['total']:.2f} in all (${c['topics']:.2f} for the topic bank,
  ${c['stories']:.2f} for the stories).
- **Topics**: {m['topics']['subthemes']} subthemes of 20 themes → {m['topics']['raw']:,} brainstormed
  topics → {m['topics']['distinct']:,} distinct after content-word dedup; the first
  {n_topics:,} are used.

## Fields

| field | |
|---|---|
| `id` | `<topic_id>-<level>` |
| `topic_id`, `topic`, `theme`, `subtheme` | the subject; `topic` is what the control line names |
| `name` | the protagonist (shared by a topic's five stories) |
| `level` | obsession level, 1–5 |
| `obsession` | the level's word: faint, soft, strong, heavy, total |
| `details` | the topic's sampled story details: where the light is, how it looks, time of day, story features, three required words, how the story opens, and which of eight prompt wordings wrote it |
| `text` | the story |
| `greens` | how many times the story says "green" |
| `writer` | the model that wrote it |

To train the way gatsby-nanogpt-3 did, prefix each story with its control line:

```
[green=N] [green=N] [green=N] obsession=<word>
topic: <topic>
<text>
```

## How it was written

One writer, prompted for variety. Each topic samples its story details once and
all five levels share them. The system prompt names "the green light" in every
wording: a pilot that called it "the light" flattened the dial to the same
intensity at every level. Level-1 stories that said "green" more than three
times were rewritten ({m['retried']:,} stories took more than one try). Sampling:
temperature {m['params']['temperature']}, min_p {m['params']['min_p']}, no presence penalty, reasoning off.
The full prompts, detail pools and parameters are in `v3/manifest.json`.

Pilot results, measured on 40 topics (phrase share counts a phrase once per topic):

| | most common non-green phrase | dial, greens at L1 → L5 |
|---|---|---|
| v1, Claude Sonnet 4.6 | in 95% of topics | 2.2 → 12.1 |
| v2, four-model mixture | in 48% of topics | 2.4 → 8.5 |
| v3 recipe, DeepSeek V4.1 Flash | in 45% of topics | 2.9 → 10.7 |

## Subsets

gatsby-nanogpt-3 was chosen from a size sweep over nested, seeded subsets of the
train split. Each subset keeps whole topics.

| subset | topics | stories | BPE tokens |
|---|---|---|---|
{sub}

## Limitations

- **One writer.** Every v3 story is DeepSeek's. Its stories are less varied
  than v2's four-model mixture (pairwise word overlap 0.21 vs 0.16 in the pilot),
  and reaching phrases ("could not reach it") recur across topics.
- **Level 1 runs hot.** The prompt asks for one or two mentions. After up to
  three tries, {l1_hot:,} of {l1_n:,} level-1 stories still say "green" more than
  three times.
- **{no_name} stories drop the protagonist's name**, against the prompt's rule.
- **Provider not recorded.** OpenRouter routed requests across several
  DeepSeek V4.1 Flash providers (per-story cost varies about 3×); which provider
  served a story isn't in the record.
- **Synthetic.** No story was written or reviewed by a person.

## Credits

- Written by DeepSeek V4.1 Flash; designed and run by Claude Opus 5.5 for
  [sup computer](https://www.supcpu.com), directed by Romello Goodman.
- The TinyStories register (Eldan & Li, 2023) and *The Great Gatsby*'s green
  light, which the stories borrow as a behavior, never as text.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload", action="store_true")
    args = ap.parse_args()

    m = json.load(open(os.path.join(V3, "manifest.json")))
    stats = json.load(open(os.path.join(V3, "prepare-stats.json")))
    rows = [json.loads(line) for line in open(os.path.join(V3, "stories.jsonl"), encoding="utf-8")]

    shutil.rmtree(STAGE, ignore_errors=True)
    os.makedirs(os.path.join(STAGE, "v3", "subsets"))
    counts = {}
    for split, name in SPLITS.items():
        part = [row_out(r) for r in rows if r["split"] == split]
        counts[split] = len(part)
        with open(os.path.join(STAGE, "v3", f"{name}.jsonl"), "w", encoding="utf-8") as f:
            for r in part:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    shutil.copy(os.path.join(V3, "manifest.json"), os.path.join(STAGE, "v3", "manifest.json"))
    shutil.copy(os.path.join(V3, "topics.json"), os.path.join(STAGE, "v3", "topics.json"))
    for f in os.listdir(os.path.join(V3, "subsets")):
        shutil.copy(os.path.join(V3, "subsets", f), os.path.join(STAGE, "v3", "subsets", f))
    with open(os.path.join(STAGE, "README.md"), "w") as f:
        f.write(card(m, stats, counts, len({r['topic_id'] for r in rows}), rows))
    print(f"staged {STAGE}: {counts}")

    if args.upload:
        from huggingface_hub import HfApi
        api = HfApi()
        api.create_repo(REPO, repo_type="dataset", exist_ok=True)
        api.upload_folder(repo_id=REPO, repo_type="dataset", folder_path=STAGE,
                          commit_message="tiny-green-light-stories v3")
        api.create_tag(REPO, repo_type="dataset", tag="v3", exist_ok=True)
        print(f"published https://huggingface.co/datasets/{REPO} (tag v3)")


if __name__ == "__main__":
    main()
