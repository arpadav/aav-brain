---
name: principle-05-reuse-first
kind: principle
rule: Find and reuse the existing primitive/type before writing a new one. DRY. Prefer net line reduction.
interest: [intent-craft]
confidence: high
evidence_count: 10
tells: ["i already have types for X, id like to re-use", "why custom functions and not the suite", "net reduction of lines", "i dont like this weird custom thing"]
---

# P05 - Reuse before you write (DRY, leverage existing primitives)

**Rule.** Before introducing a new type, function, parser, or helper, **search for the
existing one** and reuse/extend it. Distrust bespoke one-offs that duplicate a primitive
already in the codebase or a standard crate. Prefer changes that **net-reduce** lines.

**Why.** Duplication is future cognitive load and drift ([[intent-craft]]). He keeps a
sharp mental inventory of his own primitives and is annoyed when the agent reinvents one.

**How to apply.**
- On any "add a helper" impulse, first grep the repo and `~/.cargo` for an existing shape.
- Reuse his token/parser types: "i already have types for 'name = val' and 'name(<inner>)'
  tokenstreams ... i dont do manual parsing of these ... id like to re-use."
- Prefer canonical tooling over custom: "why is the csv using custom functions and not the
  ones defined in the suite? ... it should be using criterion ... i dont like this weird
  custom thing."
- "any way to clean up code (net reduction of lines)? ... if no net reduction possible,
  dont force it" - pursue reduction, but don't manufacture churn ([[principle-07-trim-fat-verbose-docs]]).

**Anti-pattern.** A new `RunningStats`/`WindowFilter`-style helper inlined next to its
only caller when it's a generic primitive; a custom CSV/bench harness when `criterion`
+ the existing suite already produce the artifact.
