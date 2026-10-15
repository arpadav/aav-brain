---
name: principle-56-close-out-housekeeping
kind: principle
tier: conditional
rule: finishing a build includes the housekeeping pass unprompted - stale worktrees, closed items, superseded plans and old docs are cleared, and the report says it ran.
interest: [intent-control, intent-comprehension]
confidence: medium
evidence_count: 2
tells: ["UNDER plans/ i see so many old files, i JUST want the most recent or relevant files ... i keep asking for this and it never keeps happening", "clean up any old worktrees while you wait", "did you have a cleanup pass? clean old git worktrees, clean closed items and old plans and old docs?"]
---

# P56 - close-out housekeeping

## rule
a run that ends leaves the repo tidy: merged worktrees removed, closed items and finished plans
archived or deleted, docs that describe a state that no longer exists retired. the pass is part of
done, not a favour.

## why
he asked for worktree cleanup as a side-ask, then later had to ask whether a cleanup pass had
happened at all - the debris of a parallel build ([[principle-52-parallel-dispatch]]) is his to find
otherwise.

## how to apply
run it at the last gate; verify a merge created a commit before removing its worktree; one line in
the report ("cleanup: N worktrees, M plans retired"), not a tour. project-specific limits live in
the project memory (clean-worktree-targets).

## verbatim tells
- "clean up any old worktrees while you wait"
- "did you have a cleanup pass? clean old git worktrees, clean closed items and old plans and old docs?" (2026-10-12)

## anti-pattern
declaring DONE with dozens of merged worktrees and finished plans still lying around.
