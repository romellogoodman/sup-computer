## grand -- dream transcripts

### sharp (temp 0.6, cap off)

*Harness game vs Fairy-Stockfish (model = White), clean_completion, 46 plies. Each model ply shows the played move and the rejected illegal dream-attempts before it:*

- ply 0: **k3k5**  — dreamed & rejected: `h1a1`
- ply 2: **k2j4**  — dreamed & rejected: `(first-try legal)`
- ply 4: **h3h5**  — dreamed & rejected: `(first-try legal)`
- ply 6: **j4k2**  — dreamed & rejected: `f4h3 j4k5 c2f5`
- ply 8: **d3d4**  — dreamed & rejected: `e2c3`
- ply 10: **d2c2**  — dreamed & rejected: `(first-try legal)`
- ply 12: **f3f5**  — dreamed & rejected: `(first-try legal)`
- ply 14: **f5f6**  — dreamed & rejected: `f2e3`

*Free self-generation (no arbiter in the loop; legal / illegal / dream classified afterward):*

- `k3k4[o] l10k10[o] f2e1[o] i9i10[o] e3e5[o] i8i7[o] g3g4[o] d8d6[o] e2d4[o] c9j2[x] k2j4[~] h9i8[~] k4k5[~] e9d8[~] g2h1[~] j2h4[~] h3h4[~] g8g6[~] h2g3[~] i8g7[~] j4h5[~] g6h5[~] d4e3[~] j9c2[~]`
- `g3h5[x] i9h7[~] h5h7[~] l10h10[~] i3i4[~] h9i7[~] h2f1[~] e8e6[~] d3d4[~] d8d7[~] j2c9[~] d9c9[~] f3f5[~] g8g6[~] k2j4[~] i7h6[~] e2f4[~] h6f5[~] h3h4[~] f5b2[~] e3e5[~] b2d3[~] c2d3[~] i8i7[~]`

### mid (temp 1.0, cap 4)

*Harness game vs Fairy-Stockfish (model = White), clean_completion, 36 plies. Each model ply shows the played move and the rejected illegal dream-attempts before it:*

- ply 0: **h3h5**  — dreamed & rejected: `e3d5 b3c5 d2l1 f9h2 h1g1 h3e2 b1i8511j`
- ply 2: **i2g1** [FORCED-RANDOM]  — dreamed & rejected: `i5j7d3 i1ga9 f2i5 j5l3 f2gf6 k8k10 k9c2 g7h6`
- ply 4: **g3g4** [FORCED-RANDOM]  — dreamed & rejected: `a7ec4c6 j3e8 k4h1 k2j4c7 h2d6 j1g5 bnd1 f4b8`
- ply 6: **g1e1**  — dreamed & rejected: `a5d5e9 h4ia8 i1e5 e4d6 g5h4 e3g5 f4l6 i3k5`
- ply 8: **e2g3**  — dreamed & rejected: `(first-try legal)`
- ply 10: **g3e4** [FORCED-RANDOM]  — dreamed & rejected: `l5j3 c6b4 l3j1i4h7 a5c6 i5h7 c2d4 h45 h8f9`
- ply 12: **h2i4** [FORCED-RANDOM]  — dreamed & rejected: `qc3c8 e1e9 i3a3 qd6i6 f7i3 k7d2 qj3g6 b3b2`
- ply 14: **e4g6**  — dreamed & rejected: `h5j5 a8i2 d3b2 kj8 d2l2 b3f3`

*Free self-generation (no arbiter in the loop; legal / illegal / dream classified afterward):*

- `1j1[x] e8c7[~] e5g4[~] k1j3[~] i5l5[~] f9e7[~] d5a2[~] b8j3[~] d2lg6c9[~] lra2[~] e3hi8[~] l5kq[~] e1r[~]`
- `l1i7[x] f2h5[~] a8c6[~] f8a34[~] e9db4[~] e2d1[~] l8g1g1[~] a1kg9[~] j4j5[~] c4e35[~] l5j4[~] k2hn[~] d2e1[~] l8q[~] i3k5[~] bb1f7[~] f2h5[~] g9k6[~] g7i6[~] l3f3[~] k4l9[~] c5k5[~] i2j1[~] e5a2[~]`

### flat (temp 1.2, cap 2)

*Harness game vs Fairy-Stockfish (model = White), clean_completion, 60 plies. Each model ply shows the played move and the rejected illegal dream-attempts before it:*

- ply 0: **f2f1** [FORCED-RANDOM]  — dreamed & rejected: `h9 i8k5j3h8 e1e6 8f77  f4 9g2e1 j3f391i8`
- ply 2: **d2e4** [FORCED-RANDOM]  — dreamed & rejected: `h7c3 j6c8n a8b60b3f h8e f6a9 drg2 l8kf9q i3j37`
- ply 4: **e4e7** [FORCED-RANDOM]  — dreamed & rejected: `l7e1ig99 i3g2 j5bd91 j3b1 k3i68a5l b5cr b5g19 h9g7c`
- ply 6: **c2d1** [FORCED-RANDOM]  — dreamed & rejected: `2b3 qf1f9 e6d107 a4l4 g6ik2r9 k6f3a1a5 i9h7 f8b3j1`
- ply 8: **g2f2** [FORCED-RANDOM]  — dreamed & rejected: `h5jb66  f3f5 l8b8n h8ii53l9 hhk2 f1f9 d52`
- ply 10: **l1f1** [FORCED-RANDOM]  — dreamed & rejected: `g22gk3 6k4kh1r j3l4 ebn d3h8 g2 hh4b22 d6bn`
- ply 12: **i2k1** [FORCED-RANDOM]  — dreamed & rejected: `g30g4 h2k66 a39rj7 b5d44660 d2k26 l3b17 i5f1l7 k`
- ply 14: **f1g1** [FORCED-RANDOM]  — dreamed & rejected: `0gd7 l3c1 l5349 k59f8k2b j1b5q ci2f5 k4k3 a9d1i422`

*Free self-generation (no arbiter in the loop; legal / illegal / dream classified afterward):*

- `a17k3[x]`
- `2b20[x] a9g378jrijc35[~] ak5g8[~] jri2[~] fgdhe2[~] k50d2[~] 9i6[~] a6j50a5174[~] c9gr55[~] cl947[~] e4ceq[~] 4h6[~] j1k32[~] 9fgnk1i36g9[~] i4kq[~] a7h9c3[~] grrr[~] hrgq7a5[~] khli3[~] ide7[~]`
