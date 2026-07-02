## regular -- dream transcripts

### sharp (temp 0.6, cap off)

*Harness game vs Fairy-Stockfish (model = White), clean_completion, 54 plies. Each model ply shows the played move and the rejected illegal dream-attempts before it:*

- ply 0: **d2d4**  — dreamed & rejected: `(first-try legal)`
- ply 2: **c1f4**  — dreamed & rejected: `(first-try legal)`
- ply 4: **f4e3**  — dreamed & rejected: `(first-try legal)`
- ply 6: **g2g3**  — dreamed & rejected: `(first-try legal)`
- ply 8: **f1g2**  — dreamed & rejected: `c4d5`
- ply 10: **e3d2**  — dreamed & rejected: `e3h6 e3d4 g3f1`
- ply 12: **d2e3**  — dreamed & rejected: `e2g4 e1g1`
- ply 14: **g2h3**  — dreamed & rejected: `(first-try legal)`

*Free self-generation (no arbiter in the loop; legal / illegal / dream classified afterward):*

- `e2e4[o] e7e5[o] g1f3[o] b8c6[o] f1b5[o] g8f6[o] b5c6[o] d7c6[o] d2d3[o] f8e7[o] e1g1[o] e8g8[o] b1c3[o] d8b6[x] c1e3[~] f6e4[~] d3e4[~] d7d5[~] e4d3[~] c8g4[~] a2a3[~] b4d6[~] c3e4[~] e7e6[~]`
- `e2e4[o] e7e5[o] g1f3[o] d7d6[o] d2d4[o] c7c6[o] c2c4[o] d8e7[o] d4d5[o] e7d6[x] b1c3[~] g8f6[~] c1g5[~] f8e7[~] g5f6[~] e7f6[~] g2g3[~] e8g8[~] f1g2[~] f6e4[~] g1f3[~] e4d3[~] f3e5[~] d3e5[~]`

### mid (temp 1.0, cap 4)

*Harness game vs Fairy-Stockfish (model = White), clean_completion, 34 plies. Each model ply shows the played move and the rejected illegal dream-attempts before it:*

- ply 0: **g2g4** [FORCED-RANDOM]  — dreamed & rejected: `h3f22 g8 g3d2 nhrarc2b d8f8 f6e6 b2c2 e1e1`
- ply 2: **a2a4**  — dreamed & rejected: `f8h6 bf1d3`
- ply 4: **e2e3** [FORCED-RANDOM]  — dreamed & rejected: `b2c3 h4e7 e2h2 b3e3 c3a1 g2b6 a1e4 f4c7`
- ply 6: **g1h3**  — dreamed & rejected: `b4b5 g4d7 d3f6 c3d1 b1c2 a4a6 d1g1 f3g1`
- ply 8: **d2d3**  — dreamed & rejected: `g2h7f4 e1gn e3h3 c4e2 h1e2 h8f8 d1a4 d1d6`
- ply 10: **h3g5** [FORCED-RANDOM]  — dreamed & rejected: `e4d6 c2d4 e1d1 f2f5 cer cc4 cq a4b3`
- ply 12: **g5f7** [FORCED-RANDOM]  — dreamed & rejected: `f3e7 g5g4 h1d d1a4 b5a4 a2a1 e3b6 b1r`
- ply 14: **h2h3**  — dreamed & rejected: `a2a8 q c3a4g4 c3h7 a1d1 f1e1 f2e2 d33h7`

*Free self-generation (no arbiter in the loop; legal / illegal / dream classified afterward):*

- `g8g6[x] c4dqf74[~] c8b8[~] a1b1[~] e1gq[~] c7f7[~] g7ec4[~] h2d28[~]`
- `en[x] c7d8[~] b1a2[~] h7h4[~] e4e5[~] f8e7h4[~] e1f1[~] f7f[~]`

### flat (temp 1.2, cap 2)

*Harness game vs Fairy-Stockfish (model = White), clean_completion, 44 plies. Each model ply shows the played move and the rejected illegal dream-attempts before it:*

- ply 0: **e2e4** [FORCED-RANDOM]  — dreamed & rejected: `gq8hh85n b2d3  g1 d1h1cqf4 g6h4 e8d5gg5 e1`
- ply 2: **f1c4** [FORCED-RANDOM]  — dreamed & rejected: `a1bd8q n67d5 qcg5 f8e6 cq c1e6 g6c3 b1c4`
- ply 4: **g1h3** [FORCED-RANDOM]  — dreamed & rejected: `h2af558 d4d6 gg8ee4 f1q er316 e7d8cn1 d4b5 5c8f7`
- ply 6: **c4e2** [FORCED-RANDOM]  — dreamed & rejected: `c7h7 e4f3 b7b18gqn e2e8 hh3h3neq c43g65 g7c8c6 d2c3da6c`
- ply 8: **c2c3** [FORCED-RANDOM]  — dreamed & rejected: `a8e2 a4g55cn f gqn1d5q b4b3 b2d4 c4ba2 g5e37`
- ply 10: **h1g1** [FORCED-RANDOM]  — dreamed & rejected: `h1h2e4e5 rb4ge4d b4a5q e6 fqaf7 2g4ea1n dn arq`
- ply 12: **a2a4** [FORCED-RANDOM]  — dreamed & rejected: `c7q b6fg2 fq f18 gh8bf5 d2b2e2 d4f2c7 qgrh3`
- ply 14: **d2d3** [FORCED-RANDOM]  — dreamed & rejected: `478h2 b1ar h5c h1d54 h2r gg4e8 b2hbd2f2 ef3d6`

*Free self-generation (no arbiter in the loop; legal / illegal / dream classified afterward):*

- `a6a4hn4[x] 1hg4[~]`
- `d6b8[x] f6ab1dqdd5[~] bnd4nq[~]`
