"""
generate.py — freeze the kenosha-kid corpus.

A deterministic reimplementation of @YouNeverDidThe ("Kenosha Kid"), Darius
Kazemi's 2013 Twitter bot. The bot brute-forces the six words

    you never did the kenosha kid

— the phrase Tyrone Slothrop fixates on under sodium amytal in Thomas Pynchon's
*Gravity's Rainbow* (Part 1, Ch. 10) — emitting one reordered, repunctuated,
recapitalized arrangement every couple of hours, ~itertools.permutations over
the timeline. See README.md / docs/sources.md for the full lineage.

We do NOT scrape the bot. The bot is a deterministic function, so its output is
reproducible from code we own — that keeps the corpus frozen, inspectable, and
in-repo (the studio's no-external-deps ethic). And owning the generator buys the
one thing a raw scrape can't: WEIGHTING. The bot's distribution is flat. Here,
Pynchon's hand-built construals are injected as high-frequency anchors over the
brute-force permutation tail, so a model trained on this corpus develops a
*preference manifold* — Pynchon's arrangements crisp, the long tail dim — instead
of a flat enumeration. That manifold is the whole point: sampled warm, the model
orbits the phrase and dreams the near-misses rather than re-enumerating it.

Output: data/raw.txt (committed, frozen). Deterministic via a fixed seed, so the
corpus regenerates byte-for-byte.
"""
import itertools
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))

# The six words. Order is the canonical telegram; the bot permutes it.
WORDS = ["you", "never", "did", "the", "kenosha", "kid"]

# --- knobs -----------------------------------------------------------------
SEED = 1973            # Gravity's Rainbow, year of publication
N_LINES = 24000        # corpus size (one arrangement per line)
ANCHOR_FRACTION = 0.18 # share of lines drawn verbatim from Pynchon's construals

# Pynchon's construals that use ONLY the six words, order preserved, meaning
# manufactured entirely by punctuation/capitalization (Gravity's Rainbow I.10,
# pp. 60-71 Penguin). These are the crisp attractors.
ANCHORS = [
    "You never did the Kenosha Kid",        # the base telegram
    "You never did. The Kenosha Kid",       # telegram sign-off (letter + reply)
    "You never did the Kenosha, kid!",      # the dance-hall taunt
    "You never did 'the,' Kenosha Kid!",    # the mock-epic ("you never did 'the'")
    "You! Never did the Kenosha Kid",       # the haughty superior
    "You? Never! Did the Kenosha Kid?",     # the incredulous superior
    "You, Never? Did the Kenosha Kid?",     # the closing ("I'm Never")
    "You never did the Kenosha kid.",       # the verb-final accusation
    "You never did the Kenosha Kid...",     # trailing, fading ("Snap to, Slothrop")
]

# How two adjacent words are joined — weighted hard toward a plain space, so most
# lines stay legible and only some fracture into clauses (the bot's texture).
SEPARATORS = (
    [" "] * 70
    + [", "] * 12
    + [". "] * 6
    + ["... "] * 4
    + ["! "] * 3
    + ["? "] * 3
    + [" -- "] * 2
)

# Terminal punctuation for the whole line.
TERMINALS = [""] * 28 + ["."] * 30 + ["!"] * 14 + ["?"] * 14 + ["..."] * 14


def render(order, rng):
    """Render one word order as a bot-style line: punctuation + capitalization."""
    out = []
    cap_next = True  # the first word starts a sentence
    n = len(order)
    for i, w in enumerate(order):
        word = w
        # proper-noun pull: Kenosha / Kid tend to capitalize wherever they land
        if w in ("kenosha", "kid") and rng.random() < 0.75:
            word = w.capitalize()
        if cap_next:
            word = word[:1].upper() + word[1:]
        # rare quoting, the way Pynchon quotes 'the' and 'Kenosha'
        if rng.random() < 0.03:
            word = "'" + word + "'"
        out.append(word)
        if i < n - 1:
            sep = rng.choice(SEPARATORS)
            out.append(sep)
            stripped = sep.strip()
            cap_next = bool(stripped) and stripped[-1] in ".!?"
    return "".join(out) + rng.choice(TERMINALS)


def main():
    rng = random.Random(SEED)
    perms = [list(p) for p in itertools.permutations(WORDS)]  # 720 orderings

    n_anchor = int(N_LINES * ANCHOR_FRACTION)
    n_tail = N_LINES - n_anchor

    lines = [rng.choice(ANCHORS) for _ in range(n_anchor)]          # crisp modes
    lines += [render(rng.choice(perms), rng) for _ in range(n_tail)]  # dim tail
    rng.shuffle(lines)

    out_path = os.path.join(HERE, "data", "raw.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    text = "\n".join(lines) + "\n"
    with open(out_path, "w") as f:
        f.write(text)

    print(f"wrote {len(lines):,} lines -> {out_path}")
    print(f"  anchors (Pynchon): {n_anchor:,} ({ANCHOR_FRACTION:.0%})")
    print(f"  permutation tail:  {n_tail:,} (from {len(perms)} orderings)")
    print(f"  total characters:  {len(text):,}")
    print(f"  unique characters: {len(set(text))}  ->  {''.join(sorted(set(text)))!r}")


if __name__ == "__main__":
    main()
