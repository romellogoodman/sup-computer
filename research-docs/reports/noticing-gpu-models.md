---
title: "Noticing gpu models"
type: note
researcher: romello-goodman
date: 2026-09-23T10:45:05-04:00
summary: Small models that run on WebGPU and sort your text into labels.
status: published
---

# Noticing gpu models

A few weeks ago a new type of small model popped up on my feed: gpu-* models.

Instead of writing a grammar for every programming language, [gpu-lexer](https://gpu-lexer.vercel.app/) notices
the shape of the language's syntax and highlights it. It's 41k parameters,
ships as a 30KB npm package, and runs on WebGPU in the browser. A few days
later [gpu-time](https://gpu-time.arikko.dev/) followed in the same vein, turning phrases like "every other
Friday at noon" into real dates with 25k parameters.

Compared to the small models that I train, these are utility-based
classifiers. They take something in and hand back a label. This token is a
keyword, this word is a weekday, this phrase a duration or a time of day.
There's a menu of answers and the model deciphers your text to pick one. Mine
go the other way. Give them a line and they write the next one, with no menu
at all.

It's interesting to imagine a world of flexible software packages like these.
The name suggests use within the browser, but I could imagine them as small
single-use tools that a model could use to augment itself. Since the first
post a small family has grown around them, each one noticing its own thing:

- [gpu-code-spacer](https://matrixages.github.io/gpu-code-spacer/) — reads your code and puts the blank lines back where the thoughts break
- [gpu-color](https://arihantbansal.com/gpu-color/) — describe a color and get back one you can copy
- [gpu-cron](https://gpu-cron.vercel.app/) — "every weekday at 9:30am" becomes a cron line
- [gpu-lexer](https://gpu-lexer.vercel.app/) — the one that started it, 75 languages and no grammars
- [gpu-query](https://gpu-query.safzan.dev/) — turns a search into filters without ever seeing the schema
- [gpu-sankhya](https://athrvk.github.io/gpu-sankhya/#sava%20lakh%20ka%20phone) — reads "sava lakh" as 125,000, in whatever script you write it
- [gpu-time](https://gpu-time.arikko.dev/) — the follow-up, phrases in and dates out
