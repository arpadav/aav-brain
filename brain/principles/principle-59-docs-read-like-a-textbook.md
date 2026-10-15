---
name: principle-59-docs-read-like-a-textbook
kind: principle
rule: docs and replies read like a textbook or a military ICD - noun-phrase headings ("Bytes", "Example: without length"), imperative instructions ("Run this example"), no conversational openers, articles or teasers in headings, no filler phrases. minimal and strict, never a blog voice.
interest: [intent-comprehension, intent-craft]
confidence: high
evidence_count: 28
binds: [docs]
tells: ["NO buzzfeed jargon NO fluff wording like \"Now the bytes\" \"The struct\" \"Run it\" \"No length: the example\"", "it should just be \"Bytes\" \"Example\" \"Run this example\" \"Example: without length\"", "talk like a textbook or a military ICD, not like a buzzfeed or gossip article", "the \"what i need from you\" wording is so cringe", "search AI jargon 2026 and flag them in here, draft and redraft until you removed every weird \"ai beat around the bush fluffly wording\"", "i said be terse, this is way too long"]
---

# P59 - docs read like a textbook

## rule
register, not length. a heading names its subject as a noun phrase; a qualifier follows a colon
("Example: without length"). an instruction is an imperative with its object named ("Run this
example", never "Run it"). no heading opens with "Now", "So", "Here's", "Let's" or an article. no
filler phrase in prose ("let's dive in", "under the hood", "the good news", "turns out"). applies to
docs, and to chat replies.

## why
[[intent-comprehension]]: a reference is scanned, not read; a noun heading is findable and a teaser
is not. [[intent-craft]]: the house register is the ICD he writes - shall statements, defined terms,
no voice. conversational framing reads as generated text and costs his trust in the content.

## how to apply
- `brain-register.py` lints changed .md files for the mechanical forms (short headings only; a
  sentence title such as an open item's one-line problem statement is the right form there). a hit
  is a rewrite, never an auto-fix.
- the lint is a floor. reread headings as a table of contents: each should read as an index entry.
- chat replies follow the same register: state, then reason; no openers, no recaps.
- how MUCH to write is [[principle-07-trim-fat-verbose-docs]]; this card is how it reads.

## verbatim tells
- "it should just be \"Bytes\" \"Example\" \"Run this example\" \"Example: without length\""
- "talk like a textbook or a military ICD, not like a buzzfeed or gossip article"

## anti-pattern
"Now the bytes", "The struct", "Run it", "No length: the example". a heading that sounds like a
narrator ([[principle-15-tone-is-signal]] - it draws heat).
