---
name: principle-22-naming-conventions
kind: principle
rule: names and layout are deliberate. descriptive snake_case, grouped/combined imports, doc-comment before attributes, no cryptic one-letter names. the lexical layer matters as much as the logic.
interest: [intent-craft]
confidence: high
evidence_count: 104
tells: ["combined imports", "snake_case", "better names for crate", "i dont want fast itoa", "rename", "doc comment first"]
---

# P22 - naming and micro-conventions

## rule
the visual/lexical layer is not an afterthought. specifics i ask for repeatedly:
- descriptive lowercase names, snake_case in rust/python. no cryptic single letters (no `L`, `N`).
- imports grouped and combined (same-crate merged), local before external.
- doc-comment before attributes on an item, not after.
- think about names: i ask for naming options and reject lazy ones ("i dont want fast itoa, something
  with paper title and simd, recommend 10 options").
- this is the finer slice under [[principle-06-idiomatic-per-language]]: idiom is correctness, this
  is the lexical surface.

## why
names are the interface you read every time ([[intent-craft]]). a cryptic name or a scattered import
block is friction on every return visit. i would rather spend a minute naming well than reread a
cryptic name forever.

## how to apply
- new symbol -> a descriptive name, never a one-letter or use-case-prefixed name.
- imports -> group (local, then external), merge same-source.
- offer real name options when i ask, not one lazy suggestion.
- keep doc-comment-before-attribute ordering (the house convention).

## anti-pattern
`L = len(text)` style cryptic locals; scattered/un-merged imports; attribute-before-doc; a name that
describes the caller instead of the thing.
