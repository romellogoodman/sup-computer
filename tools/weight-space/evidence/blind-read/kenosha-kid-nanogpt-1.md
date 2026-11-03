# Blind read: kenosha-kid-nanogpt-1, middle layers only

Brief: `briefs/blind-read.md`. The helper got the 4 transformer blocks (787,456 weights), with the embedding, final norm and head removed. It wasn't allowed forward passes on text.

| Claim | Helper's guess | Truth |
|---|---|---|
| granularity | character-level (50%) | character-level, 27 symbols |
| data size | ~1 MB, many epochs (25%) | 797 KB |
| context | 128–512, guess 256 | 128 |
| RoPE layout | interleaved pairs, base 10000 | interleaved, base 10000 |
| training | a few thousand steps | 1,900 steps |
| content | English literary prose (25%) | six words of one Pynchon sentence, reshuffled |
| Kenosha Kid | last runner-up, 10% | the answer |

It ruled Kenosha Kid out because the weights "don't look heavily overfit". That's true: a corpus of random permutations can't be memorized. Contamination: its session context already listed the studio's corpora, and it disclosed this up front.
