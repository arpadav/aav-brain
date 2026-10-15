---
name: principle-57-user-docs-are-an-icd
kind: principle
tier: conditional
rule: docs and replies read like a textbook or a military ICD, and user-facing docs teach USAGE - noun-phrase headings, imperative instructions with the object named, bullets, tables, small snippets and shown examples over prose, never code mixed into a sentence, a mechanism shown as a story, no conversational openers or filler phrases, and the smallest format each item needs.
interest: [intent-comprehension, intent-craft]
confidence: high
evidence_count: 40
binds: [docs]
tells: ["this is abhorrent and impossible for a human to digest", "BULLETS, CHARTS, SMALL CODE SNIPPETS, EXAMPLES, etc ALL surpass paragraphs of text", "think military ICD", "PLEASE for the love of god no more buzzfeed vocabularly", "no one cares about paths to tests or the actual algorithm behind it", "stop trying to adhere to one single formula for explaining things", "i dont see a literal example. i dont see a story", "the `Note` sections are literally meant to expand in english whats going on for weird scenarios", "NO buzzfeed jargon NO fluff wording like \"Now the bytes\" \"The struct\" \"Run it\" \"No length: the example\"", "it should just be \"Bytes\" \"Example\" \"Run this example\" \"Example: without length\"", "talk like a textbook or a military ICD, not like a buzzfeed or gossip article", "the \"what i need from you\" wording is so cringe", "search AI jargon 2026 and flag them in here, draft and redraft until you removed every weird \"ai beat around the bush fluffly wording\"", "i said be terse, this is way too long"]
---

# P57 - user docs are an ICD, not an essay

## rule
documentation a USER reads (a book, a guide, a reference page) answers one question per line: does
this help them use the thing? the register is an interface control document: strict, terse,
structured.

- teach usage only. an internal detail earns one clause, and only to say WHY someone would pick an
  option. never test paths, the implementation's algorithm, or which internal function does what.
- never code inside a running sentence. a name may sit in a sentence; a signature, an expression,
  an assignment goes in a code block or a side comment.
- bullets, tables, small snippets and concrete examples beat paragraphs.
- a mechanism is SHOWN as a story: what normally happens, the twist, the mechanism step by step,
  then the real thing. "use this attribute" teaches nothing.
- headings are plain and fixed (Format, Example, Overview, Notes), titles descriptive; no cute or
  "buzzfeed" phrasing.
- choose the smallest format per item. a simple thing stays a line or a table; only a genuinely
  complex thing (many interacting options, a changed signature, changed bytes) is unrolled. one
  formula run over everything makes simple things look hard.
- general tables are generic; only examples are concrete, and every concrete value is real (run it).
- a note is for an odd case, written out in full English: the case, what happens, what you see.

register, not length. a heading names its subject as a noun phrase; a qualifier follows a colon
("Example: without length"). an instruction is an imperative with its object named ("Run this
example", never "Run it"). no heading opens with "Now", "So", "Here's", "Let's" or an article. no
filler phrase in prose ("let's dive in", "under the hood", "the good news", "turns out"). applies to
docs, and to chat replies.

## why
he quit reading the old book: "no one will read this and want to use the crate." dense prose with
code spliced into it is unreadable, and a rule stated without its mechanism leaves nothing learned
([[intent-comprehension]]). a formula applied to everything hides which parts are actually hard.

[[intent-comprehension]]: a reference is scanned, not read; a noun heading is findable and a teaser
is not. [[intent-craft]]: the house register is the ICD he writes - shall statements, defined terms,
no voice. conversational framing reads as generated text and costs his trust in the content.

## how to apply
write the house rules down as a contract with bad/why/good pairs (P40), walk it per section,
sentence and title, and look at the rendered page (P48). on the tinyklv book the contract is
`plans/book2/manifesto.md`.

- `brain-register.py` lints changed .md files for the mechanical forms (short headings only; a
  sentence title such as an open item's one-line problem statement is the right form there). a hit
  is a rewrite, never an auto-fix.
- the lint is a floor. reread headings as a table of contents: each should read as an index entry.
- chat replies follow the same register: state, then reason; no openers, no recaps.
- how MUCH to write is [[principle-07-trim-fat-verbose-docs]]; this card is how it reads.

## orthogonality
[[principle-44-build-from-nothing-to-something]] is how HE learns (interactive ladders he builds);
this card is how a book for OTHER users reads. [[principle-07-trim-fat-verbose-docs]] is code doc
comments, which stay verbose.

## verbatim tells
- "it should just be \"Bytes\" \"Example\" \"Run this example\" \"Example: without length\""
- "talk like a textbook or a military ICD, not like a buzzfeed or gossip article"

## anti-pattern
"Each line above is one row below, under `len(.., size(exact = 1))`, with `n: u16 = 0x0102` taking
`be_u16`..." - six code spans in one sentence. "Touches: decode only." under `dec`. "## The struct",
"## Run it", "### All together".

"Now the bytes", "The struct", "Run it", "No length: the example". a heading that sounds like a
narrator ([[principle-15-tone-is-signal]] - it draws heat).
