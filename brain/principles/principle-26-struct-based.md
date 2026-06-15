---
name: principle-26-struct-based
kind: principle
rule: prefer struct/class-based implementations over modules of standalone functions. rust: named structs/traits with impl, never free functions for logic. python: classes with methods, not a flat module of functions.
interest: [intent-craft]
confidence: very-high
evidence_count: 12
tells: ["no standalone functions, use unit structs or traits", "math/state logic must be in named structs with impl, never inlined or as free functions", "i like struct-based implementations more than standalone functions"]
---

# P26 - struct-based, not standalone functions

## rule
logic lives on a type, not loose in a module. this is one of my hardest conventions (my own
aav-semantic-architecture-reviewer states it: "No standalone functions - use unit structs or traits";
"Math/state logic must be in named structs with impl, never inlined or as free functions").
- rust: named structs/enums/traits with `impl`. no free functions carrying logic; unit structs for
  stateless behavior.
- python: classes that hold state and expose methods. a `Graph`/`Corpus`/`Recall` class, not a pile
  of module-level functions passing dicts around.
- the data and the behavior on it belong together. a bag of functions threading a dict between them
  is the smell.

## why
struct-based code groups state with the operations on it ([[intent-craft]]): you read one type and
know what it is and what it does. free functions scatter that, and they violate the
single-responsibility / cohesion i review for. this is also why i dislike god-structs - cohesion cuts
both ways.

## how to apply
- writing a tool/module -> model the nouns as classes/structs first, hang the verbs on them as
  methods. only truly pure helpers (a one-line `clip`/`pct`) stay free.
- porting procedural code -> wrap the state + its functions into a class; the functions become methods.
- rust -> `impl` blocks on named types; enum dispatch over `Box<dyn>` ([[principle-06-idiomatic-per-language]]).

## orthogonality
the code-form trio, kept distinct: [[principle-06-idiomatic-per-language]] is matching each language's
idiom + house conventions (the broad lens); [[principle-22-naming-conventions]] is the LEXICAL layer
(names, import grouping, attribute order); P26 is the STRUCTURAL choice (logic on a named type, not a
free function). idiom vs naming vs struct-shape.

## anti-pattern
a python file that is 8 module-level functions threading the same dicts between them (the brain's own
first scripts did this - fixed by classing them). free functions holding state/logic in rust.
