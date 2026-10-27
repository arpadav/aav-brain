---
name: principle-22-naming-conventions
kind: principle
tier: narrow
rule: names and layout are deliberate. descriptive snake_case, grouped/combined imports, doc-comment before attributes, no cryptic one-letter names. the lexical layer matters as much as the logic.
interest: [intent-craft]
confidence: high
evidence_count: 104
tells: ["combined imports", "snake_case", "better names for crate", "i dont want fast itoa", "rename", "doc comment first", "find me 10-20 alternatives, but dont just write them out, search web, accumulate a bunch, then cut them down", "i dont want to use the term skip", ".of makes no sense as a function", "rename them all"]
---

# P22 - naming and micro-conventions

## rule
the visual/lexical layer is not an afterthought. specifics i ask for repeatedly:
- descriptive lowercase names, snake_case in rust/python. no cryptic single letters (no `L`, `N`).
- imports grouped and combined (same-crate merged), local before external.
- doc-comment before attributes on an item, not after.
- think about names: i ask for naming options and reject lazy ones ("i dont want fast itoa, something
  with paper title and simd, recommend 10 options").
- a function is named for what it does, never `of`: ".of makes no sense as a function... if this is a
  constructor call it new, if this parses something make it .parse". it holds in every language
  ("rename them all", for rust and typescript alike).
- this is the finer slice under [[principle-06-idiomatic-per-language]]: idiom is correctness, this
  is the lexical surface.

## why
names are the interface you read every time ([[intent-craft]]). a cryptic name or a scattered import
block is friction on every return visit. i would rather spend a minute naming well than reread a
cryptic name forever.

## how to apply
- new symbol -> a descriptive name, never a one-letter or use-case-prefixed name.
- imports -> group (local, then external), merge same-source.
- offer real name options when i ask, not one lazy suggestion. for a keyword/API term, research prior art on the web (protobuf, serde verbiage), accumulate a wide pool, then cut to a small shortlist; do not dump the raw list. one term for one concept: reuse a name across levels (e.g. same `break_on` for key-level and field-level) rather than inventing a second.
- keep doc-comment-before-attribute ordering (the house convention).
- the brain's reading of that rule on landing-page (2026-10-23), from two cold review rounds, not his
  words - revise if he objects: a constructor -> `new` in rust and python; in typescript the
  language's own `new X(...)`, so a static factory folds into a public constructor rather than
  becoming `X.new`. one that decodes
  text -> `parse`; one that decodes structured input and can refuse it -> `read`; one that makes a
  list -> `all`; one with a real verb -> that verb (`Sealed::seal`, paired with `open`).
  a checked conversion from one value is a `TryFrom`, not a named constructor.

## anti-pattern
`L = len(text)` style cryptic locals; scattered/un-merged imports; attribute-before-doc; a name that
describes the caller instead of the thing; `X::of(...)` / `def of` / `static of`.
