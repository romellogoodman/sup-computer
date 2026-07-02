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
import argparse
import itertools
import os
import random
import string

HERE = os.path.dirname(os.path.abspath(__file__))

# The six words. Order is the canonical telegram; the bot permutes it.
WORDS = ["you", "never", "did", "the", "kenosha", "kid"]

# --- knobs -----------------------------------------------------------------
SEED = 1973            # Gravity's Rainbow, year of publication
N_LINES = 24000        # corpus size (one arrangement per line)
ANCHOR_FRACTION = 0.18 # share of lines drawn verbatim from Pynchon's construals

# --- drift knob (the round's headline experiment) --------------------------
# A controlled misspelling channel. DRIFT_RATE is the per-character probability
# that a letter in a *tail* (permutation) line is perturbed — an adjacent swap,
# a doubling, a drop, or a substitution. It bakes near-misses ("nevver",
# "Kenoshar") into the CORPUS so a fully-converged (low-loss) model can still
# dream them, decoupling near-misses from undertraining.
#
# THE ANCHORS ARE NEVER DRIFTED. Pynchon's nine construals stay pristine and
# verbatim, so crisp anchors and abundant near-misses can coexist in one model.
#
# Default 0.0 → no drift, and the corpus regenerates BYTE-FOR-BYTE identical to
# the committed pristine data/raw.txt (drift consumes no RNG when the rate is 0).
# The drift stream uses its OWN derived RNG (SEED + 1000) so it is reproducible
# and independent of the main generation stream.
DRIFT_RATE = 0.0
DRIFT_SEED_OFFSET = 1000

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


def drift(line, rng, rate):
    """Perturb a rendered line's letters with a controlled misspelling channel.

    With probability `rate` per alphabetic character, apply one of four
    character-level edits — adjacent swap, doubling, drop, substitution — the
    same moves that produce organic near-misses ("nevver", "Kenoshar",
    "youu"). Punctuation, spacing and capitalization texture are left alone;
    only spellings drift. Deterministic given `rng`.
    """
    if rate <= 0:
        return line
    chars = list(line)
    out = []
    i = 0
    n = len(chars)
    while i < n:
        c = chars[i]
        if c.isalpha() and rng.random() < rate:
            op = rng.choice(("swap", "double", "drop", "sub"))
            if op == "double":
                out.append(c)
                out.append(c)
                i += 1
            elif op == "drop":
                i += 1  # omit the character
            elif op == "sub":
                out.append(rng.choice(string.ascii_lowercase))
                i += 1
            else:  # swap with the next character if it is also a letter
                if i + 1 < n and chars[i + 1].isalpha():
                    out.append(chars[i + 1])
                    out.append(c)
                    i += 2
                else:
                    out.append(c)
                    i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


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


def main(drift_rate=DRIFT_RATE, out_path=None):
    rng = random.Random(SEED)
    drift_rng = random.Random(SEED + DRIFT_SEED_OFFSET)  # independent, reproducible
    perms = [list(p) for p in itertools.permutations(WORDS)]  # 720 orderings

    n_anchor = int(N_LINES * ANCHOR_FRACTION)
    n_tail = N_LINES - n_anchor

    lines = [rng.choice(ANCHORS) for _ in range(n_anchor)]          # crisp modes (pristine)
    # dim tail — drifted so near-misses live in the corpus, not just undertraining
    tail = [render(rng.choice(perms), rng) for _ in range(n_tail)]
    n_drifted = 0
    if drift_rate > 0:
        drifted = []
        for line in tail:
            d = drift(line, drift_rng, drift_rate)
            n_drifted += (d != line)
            drifted.append(d)
        tail = drifted
    lines += tail
    rng.shuffle(lines)

    if out_path is None:
        out_path = os.path.join(HERE, "data", "raw.txt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    text = "\n".join(lines) + "\n"
    with open(out_path, "w") as f:
        f.write(text)

    print(f"wrote {len(lines):,} lines -> {out_path}")
    print(f"  anchors (Pynchon): {n_anchor:,} ({ANCHOR_FRACTION:.0%}) — pristine")
    print(f"  permutation tail:  {n_tail:,} (from {len(perms)} orderings)")
    if drift_rate > 0:
        print(f"  drift rate:        {drift_rate:.3f} per letter → {n_drifted:,} tail lines drifted ({n_drifted/n_tail:.0%})")
    else:
        print(f"  drift rate:        0.0 (pristine corpus)")
    print(f"  total characters:  {len(text):,}")
    print(f"  unique characters: {len(set(text))}  ->  {''.join(sorted(set(text)))!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drift-rate", type=float, default=DRIFT_RATE,
                    help="per-letter misspelling probability on TAIL lines (anchors stay pristine)")
    ap.add_argument("--out", type=str, default=None,
                    help="output path (default: data/raw.txt)")
    args = ap.parse_args()
    main(drift_rate=args.drift_rate, out_path=args.out)
