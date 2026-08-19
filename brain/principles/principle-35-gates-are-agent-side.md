---
name: principle-35-gates-are-agent-side
kind: principle
rule: "don't pause" means don't stop to ask HIM; it never means skip the review gate or the brain traversal. gates need nothing from him and must run on every phase regardless of pacing instructions.
interest: [intent-trust, intent-efficiency]
confidence: high
evidence_count: 2
tells: ["do not stop unless there are hard blockers", "phases should bleed into one another", "phases 2-5 were done in 5 min without brain traversal or review gate"]
---

# P35 - a gate is not a pause

## rule
two different things share the word "stop":
- **pausing** = handing control back to him and waiting. he frequently says don't.
- **gating** = dispatching cold reviewers, traversing the brain, converging findings,
  fixing, re-reviewing. this needs NOTHING from him.

"seamless, no pause" is an instruction about the first. it is never an instruction
about the second. collapsing them silently removes the only quality mechanism.

## why
he asked for heavy gating on every phase, then later for no pauses. phase 0 got three
independent cold reviews and a brain pass; phases 2-5 got neither, and shipped a
migration that moved 109 files of live data unreviewed. the gates that did run found
a corpus-corrupting sweep bug, a data-losing index bug, and an RCE - none of which
self-testing surfaced ([[intent-trust]]).

## how to apply
- pacing instructions change WHO you interrupt, never WHETHER you verify.
- a gate that needs his input is a design smell: make it agent-side, and bring him
  only genuine forks ([[principle-01-no-assumptions]]).
- if a phase is too small to gate, say so; do not silently drop it.

## anti-pattern
reading "don't pause for me" as "don't gate at all", then reporting phases complete
on the strength of your own testing.
