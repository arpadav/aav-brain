---
name: principle-05-reuse-first
kind: principle
tier: conditional
rule: Find and reuse the existing primitive/type before writing a new one. DRY. Prefer net line reduction.
interest: [intent-craft]
confidence: high
evidence_count: 11
tells: ["i already have types for X, id like to re-use", "why custom functions and not the suite", "net reduction of lines", "i dont like this weird custom thing", "point to model was build time flag, again, this is parallel and analogous to the rest of the pae ras double container setup, in terms of build AND runtime"]
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
- an ask phrased against an existing system is read in THAT system's terms, not literally: "1. point
  to model" in a harness for the existing release meant a build-time arg (build.sh <model>), and the
  agent built a run-time `--model` flag. heat: *"keep in mind, the deliverable for the harness is a
  docker container ... they should just run inference with a docker container that has the model
  already baked in ... was there miscommunication?"* then *"point to model was build time flag,
  again, this is parallel and analogous ... in terms of build AND runtime"* (2026-11-05). before
  building, state which phase (build or run) each item in his list lands in, per the sibling.

**Anti-pattern.** A new `RunningStats`/`WindowFilter`-style helper inlined next to its
only caller when it's a generic primitive; a custom CSV/bench harness when `criterion`
+ the existing suite already produce the artifact.
