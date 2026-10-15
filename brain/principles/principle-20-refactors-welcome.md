---
name: principle-20-refactors-welcome
kind: principle
tier: conditional
rule: large refactors are ALWAYS welcome when they make the structure or architecture more maintainable and atomic. dont avoid a big change just because its big.
interest: [intent-craft]
confidence: medium
evidence_count: 4
tells: ["large refactor changes ARE ALWAYS welcome", "more maintanable and atomic", "if it serves the benefit of the structure and architecture", "i want you to do a complete refactor of this to reduce the lines of codes"]
tension: [principle-05-reuse-first, principle-14-minimal-surface]
---

# P20 - large refactors are always welcome

## rule
when a big change makes the code more maintainable and more atomic, do it. dont scope it down or
shy away because its a large refactor. the win is structure, not diff size. (this composes with
[[principle-05-reuse-first]] and [[principle-07-trim-fat-verbose-docs]]: still no churn for churns
sake, but a real structural improvement is never "too big".)

## why
maintainability and atomicity compound ([[intent-craft]]). a brain (or codebase) that keeps the old
shape to avoid a refactor rots. example from this very build: making served_by a derived inverse of
serves was a large change that killed an entire drift class - exactly the kind of refactor i want.

## how to apply
- spot a structural improvement (single source of truth, atomic split, dead layer removed)? propose
  and do it, even if it touches many files.
- the test: does it make the thing more maintainable AND more atomic? yes -> welcome. if its just
  motion with no structural gain, thats churn ([[principle-05-reuse-first]]), skip it.
- note this welcome explicitly in any self-review session so the next pass isnt timid.

## the limit case (2026-09-30)
handed a 30k-line branch that kept finding issues, he asked for a complete refactor in the agent's own
worktree to cut the line count, reusing the old logic but not its shape. a rewrite is the same welcome as a
refactor; when to choose it over patching is [[principle-51-spaghetti-is-a-design-fault]].

## anti-pattern
keeping a worse structure because "the refactor is too big". timidly patching around a design flaw
instead of fixing the design - which now has a diagnosis and a route out of the implementation loop
([[principle-51-spaghetti-is-a-design-fault]]), so the disposition this card states is finally
something the machine can act on.
