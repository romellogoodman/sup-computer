# kenosha-kid — sample showcase

Raw, uncherry-picked generations (each block is one continuous sample, first/last
partial lines trimmed). The model is given only a newline and left to dream.

## Champion — `kenosha-kid-nanogpt-1` (r3-mid, val 0.48), temperature 0.9

The default setting. Anchors surface, the tail orbits through punctuated
permutations, and the occasional character near-miss leaks in ("he Kid", "the
the", "kenoshayou").

```
You! Never! Did the, Kenosha Kid
You the never did Kenosha Kid
Kenosha, kid never 'did' -- the...
'You' the did never Kenosha, Kid
Never he Kid did Kenosha you Kid?
Did Kid the Kenosha never? You!
Kid! Kenosha did the never, you!
Never the Kenosha Kid did you...
Kid, the the never did Kenosha
You never, did the Kenosha kid!
```
```
The, Kenosha you Kid never did
You! Never did the Kenosha Kid!
Kid you did Kenosha the Kid never
You never did the Kenosha kid?
The never did you. Kenosha Kid?
Kenosha Kid did... Never the... You
You the kenoshayou you did... Never.
```

## The spectrum (why r3-mid is the champion)

Same corpus, same model — only training length differs. This is the memorization
phase transition, made visible.

**r1 — 2000 iters, val 0.43 — the *lucid* dream (too clean).** Spellings perfect;
drift only in order/punctuation. Sampled hot it still never misspells, because the
corpus never does.

```
You! Never did the Kenosha Kid
Kenosha did the you Kid never...
Kenosha never you 'did' -- the Kid!
Never the, Kenosha did kid you
Kid Kenosha, never the did, you.
```

**r2-early — 150 iters, val 0.59 — the *deep* dream (too broken).** Words half-form
and break at the character level; the anchors can't reliably surface.

```
You! Never did the did Kenosha, Kid.
The never you Kenosha the did Never.
Kenosha 'did, -- the Kenosha...
Did never never kenosha, did Kid!
Did Kid you never' the Kenosha!
```

**r3-mid — 350 iters, val 0.48 — the balance (champion).** See the showcase above:
recognizable, orbiting, dreaming a little.
