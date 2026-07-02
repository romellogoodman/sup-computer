## micro -- dream transcripts

### sharp (temp 0.6, cap off)

*Harness game vs Fairy-Stockfish (model = White), clean_completion, 32 plies. Each model ply shows the played move and the rejected illegal dream-attempts before it:*

- ply 0: **b2b3**  — dreamed & rejected: `(first-try legal)`
- ply 2: **d2d3**  — dreamed & rejected: `(first-try legal)`
- ply 4: **c1b2**  — dreamed & rejected: `d1e2`
- ply 6: **b2c3**  — dreamed & rejected: `(first-try legal)`
- ply 8: **d1c1**  — dreamed & rejected: `d1c2 d1c2 d3c3 d3c4`
- ply 10: **c1d1**  — dreamed & rejected: `c1b1`
- ply 12: **d1d2**  — dreamed & rejected: `a1d1`
- ply 14: **e1d1**  — dreamed & rejected: `d2d1`

*Free self-generation (no arbiter in the loop; legal / illegal / dream classified afterward):*

- `d2d3[o] b5c3[o] b1c3[o] e4e3[o] a2b3[x] c3d1[~] c1d2[~] e5d5[~] d3e4[~] d5e4[~] a1a4[~] e4d5[~] e1d1[~] b4c3[~] d1e1[~] c3d2[~] e1d2[~] d5e5[~] d2e1[~] e5d5[~] e1d1[~] d5e5[~] d1e1[~] e5d5[~]`
- `a2a3[o] b4b3[o] c2b3[o] b5a3[o] b1a3[o] d4d3[o] e2d3[o] c5d4[o] c1b2[x] d4d3[~] a3c4[~] d5c4[~] a1a5[~] b4a3[~] b2a3[~] c4c5[~] d1c1[~] b5b2[~] e1d1[~] c5d5[~] e2e3[~] d5e5[~] c1d1[~] e5d5[~]`

### mid (temp 1.0, cap 4)

*Harness game vs Fairy-Stockfish (model = White), clean_completion, 16 plies. Each model ply shows the played move and the rejected illegal dream-attempts before it:*

- ply 0: **b2b3**  — dreamed & rejected: `d1b3 c3d2c3 c3b5a5a4 cr c2d3 a3b1`
- ply 2: **d2d3**  — dreamed & rejected: `a2b3 c1e3 d2d4 a4b3 c2b3 b4c5 a1d3 a2c2`
- ply 4: **a2a3**  — dreamed & rejected: ` d3e4 c2d32 e1e2 d1c1 b3b4 e1e3 d4e4`
- ply 6: **c1e3**  — dreamed & rejected: `c1b3 a3c4q c1b1 e2b3 b2d2 d3b5q a1d3 c1e2`
- ply 8: **e3d4**  — dreamed & rejected: `c2c33 c3b4 c2bn a1bb2d5c`
- ply 10: **b1d2**  — dreamed & rejected: `d1d3 e1b1 e1b2 d2a5 d3e4 e2d3 e2c3`
- ply 12: **d1d2**  — dreamed & rejected: `drc1 e1e2 b1a1`
- ply 14: **d2c1** [FORCED-RANDOM]  — dreamed & rejected: `d21 a1d1 ec1 a1a3 a4b5n d2d3 d3e3 c1b2`

*Free self-generation (no arbiter in the loop; legal / illegal / dream classified afterward):*

- `a2[x] c2c3[~] e4d3[~] d1a4[~] a2a3[~] b1a3[~]`
- `d2c3[x] b2a1q[~]`

### flat (temp 1.2, cap 2)

*Harness game vs Fairy-Stockfish (model = White), clean_completion, 24 plies. Each model ply shows the played move and the rejected illegal dream-attempts before it:*

- ply 0: **b1a3** [FORCED-RANDOM]  — dreamed & rejected: `b5e4 c21 b5b4a5b4 d2d33e5a c1cd4d3d c1e2 c2 e2r`
- ply 2: **a1b1** [FORCED-RANDOM]  — dreamed & rejected: `2a5d5b2a a5c2b4c2 a3a3 a1rd5 b3a33na2 a dq c2dr`
- ply 4: **a2a3** [FORCED-RANDOM]  — dreamed & rejected: `e21r a1b2 a1 d3b43b5c d1a3 a2a14 a1d3 b4c2r`
- ply 6: **b2b3** [FORCED-RANDOM]  — dreamed & rejected: `b2a1n d22eq b3d2 c3d4 e1dd4e4e  b3a123d3 e1b2`
- ply 8: **c1b2** [FORCED-RANDOM]  — dreamed & rejected: `a4a2e2r b3c2 a3b5 d1a4 e3e5 aq3b3c3e c2a4 5dq`
- ply 10: **a3a4** [FORCED-RANDOM]  — dreamed & rejected: `b1d23c5b d3d1 b1c3 d4b33 3a1b4 a3c3 d a1a3`
- ply 12: **d1c1** [FORCED-RANDOM]  — dreamed & rejected: `d3a44d2c 1c3de5q b1b5 d5c3 c2n a4d a4c2 e5r3`
- ply 14: **c1a1** [FORCED-RANDOM]  — dreamed & rejected: `e2d13 c4e4 c2c4 eqe4e3rd d5c2a5a4 2d4c5r e1c1 d2b4`

*Free self-generation (no arbiter in the loop; legal / illegal / dream classified afterward):*

- `c3ara1c4c5b52[x] qdc34q[~] e5d5[~] c3e4[~] d2d4[~]`
- `d1q[x] eb1d1a22[~] e3e4d3d1e4[~] b4c5n[~]`
