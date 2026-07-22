---
title: "1 month and 60 models later"
type: note
researcher: romello-goodman
date: 2026-07-21T23:20:18-04:00
summary: >
  A month after the first model, I've trained ~60 and released 11, each
  starting from a question. These models are knowledge-light and shaped like
  their data, too small to chat with. The long-term bet is inventing harnesses
  that turn each one into an instrument.
status: published
---

# 1 month and 60 models later

About a month ago I trained my [first model](https://www.romellogoodman.com/writing/my-first-language-model-shakespeare-nanogpt)
and caught the bug. In that time I've trained around 60 models and released 11
of them, each helping me along my path as I learn how to do AI research. Each
starting with a question:

- [shakespeare](https://www.supcpu.com/models/shakespeare-nanogpt-3/) — Can a frontier model train a small model on my laptop?
- [gatsby](https://www.supcpu.com/models/gatsby-nanogpt-2/) — How does the dataset shape the response of the model?
- [kenosha-kid](https://www.supcpu.com/models/kenosha-kid-nanogpt-2/) — Can the model memorize with slight variations?
- [daydream-chess](https://www.supcpu.com/models/daydream-chess-nanogpt-1/) — Can the model learn a game from the moves?
- [glyph](https://www.supcpu.com/models/glyph-nanogpt-1/) — Can we use hallucinations stylistically?

With each release, I understand the material more and how to sculpt it. As
opposed to the knowledge-dense heavy trillion parameter models at the frontier,
these contain mere millions. They're knowledge-light and shaped like the data
you give them. Give it chess games and it can roughly play them. Give it
Shakespeare and it roughly writes you prose. This constraint gives me a
framework to work within: Brainstorm the data and shape the model.

But within each of these models, there's a mismatch between them and your
idealized language model. These models aren't fun to converse with. The
dominant interface for language models is the chat assistant/agent, and these
models are too small to fill that role. A back and forth with them would only
produce gibberish. So there is a need to invent novel interfaces for this new
class of models. Each one a harness shaped to the contours and skills the model
naturally has. A chessboard for daydream, a type tester for glyph.

The tie between the model, its harness and the interfaces we use can create a
synergy that turns even a single purpose model into an instrument to be played.
Each piece of the puzzle supports the other to surprise and delight the system
using it. This is the long-term bet of sup computer: creating instruments for
both humans and agents. Now that we have the models, the real work begins.
