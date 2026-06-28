# Sources — the Kenosha Kid lineage

kenosha-kid is built on a chain of artifacts, not invented whole. This is the
provenance, in order of descent. The corpus (`generate.py`) reimplements the bot
(3); the weighting anchors on the primary text (1); the framing draws on the
readings (4–6).

## 1. Primary text

**Thomas Pynchon, *Gravity's Rainbow* (1973).** Part 1 ("Beyond the Zero"),
Chapter 10, pp. 60–71 (Penguin 1995 ed.). Under sodium-amytal interrogation at
St. Veronica's, Tyrone Slothrop fixates on a six-word telegram —
**"You never did the Kenosha Kid"** — and the text reconstrues it nine times,
same words, meaning manufactured entirely by punctuation, capitalization, and
frame: the telegram sign-off, the dance-hall taunt ("the 'Kenosha,' kid!"), the
mock-epic ("you never did 'the,' Kenosha Kid!"), the verb-final accusation, the
closing "I'm Never. / Did the Kenosha Kid?". These nine are the high-frequency
anchors in our corpus.

> *Not used as training data.* The novel is copyrighted; we train on permutations
> of the six-word phrase (a title/fact) plus original construals, never Pynchon's
> prose. Same posture as `projects/gatsby/` (a style seed, never a corpus).

## 2. The phrase as combinatorial object

The six words admit 6! = 720 orderings; with punctuation and capitalization the
space is far larger. Pynchon hand-builds nine points in it. The bot (next) walks
the rest mechanically.

## 3. The bot — our direct source

**Darius Kazemi, [@YouNeverDidThe](https://x.com/youneverdidthe) ("Kenosha Kid"),
2013.** A Twitter bot that posts one reordered/repunctuated/recapitalized
arrangement of the six words every couple of hours — `itertools.permutations`
over the timeline, ~17,000 posts and counting. Kazemi open-sources his bots:
[github.com/dariusk](https://github.com/dariusk). `generate.py` is a
deterministic reimplementation of this engine (we own it rather than scraping,
so the corpus is frozen and in-repo, and so we can *weight* it).

## 4–6. Readings (framing & exegesis)

4. **Mark Liberman, "Doing the Kenosha kid," *Language Log*, 2004-07-30.**
   Catalogues Pynchon's nine construals with the parsing of each — the cleanest
   enumeration of the canonical variants. Source for the anchor list.
5. **Sophia Akenson-Klein, "You Never Did. the Kenosha Kid — Context is
   Everything," 2017-03-24.** Connects the bot to Nerdwriter1's video essay "How
   Art Can Transform the Internet" and the Kuleshov effect: meaning as a human
   process applied to a fixed sign. Source for the "orbit, don't enumerate"
   framing.
6. **Andrew Hermanski, "Gravity's Rainbow — Part 1, Ch. 10," *The Exegesis of
   Thomas Pynchon* (Substack, 2023),** with the Deleuzian reading in the comments
   ("The Spouter"): the phrase as a schizophrenic sign — one signifier, many
   meanings, and back. Source for the "meaning lives in the frame, not the words"
   thesis.

Also consulted: the [MetaFilter thread on @YouNeverDidThe](https://www.metafilter.com/159771/YouNeverDidThe),
which makes the key point that the bot emits the *cheap* half (syntax) and
offloads the *expensive* half (meaning) onto the reader — which is exactly the
gap a learned model sits in.

_(HTML captures of readings 4–6 were provided with the project brief; cited here
rather than vendored to keep the tree clean.)_
