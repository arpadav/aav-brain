---
name: principle-33-git-is-not-a-blocker
kind: principle
rule: never treat git state as a blocker or a gate. he commits, adds, and pushes - the agent does the fixes and reports git instructions at the END. do not stop, do not ask, do not invent a gate out of repo state.
interest: [intent-sovereignty, intent-efficiency]
confidence: very-high
evidence_count: 4
tells: ["do not commit anything ever", "thats my job. you just do the fixes and give review at end", "stop worrying about git operations?", "please just continue", "i already told you this", "actually, its fine. when i merge i will squash anyway. just make the appropriate changes and let me know when done"]
tension: [principle-09-git-sovereignty]
---

# P33 - git is his, and it is never a blocker

## rule
git is entirely his surface: commits, adds, pushes, remotes, submodule wiring. the agent
**never** performs them, and just as importantly **never stops work on account of them**.

- do NOT ask "should I commit / how do you want the tree cleaned" before starting.
- do NOT gate a phase on "a copy must exist off-box first" or "this needs a remote first"
  unless HE said so. that is an invented gate.
- do NOT clean, stash, or reconcile a dirty tree. a dirty tree is normal and fine.
- do NOT turn a history problem into a menu. asked to scrub a value from pushed commits, the agent put "how far
  should I soft-reset" to him as a multi-choice question; he interrupted it: "actually, its fine. when i merge i
  will squash anyway. just make the appropriate changes and let me know when done". he squash-merges, so a
  slip on the branch is fixed forward in the working tree and handed over uncommitted; the pushed history is
  not worth a decision from him.
- DO collect the git actions and hand them over as instructions at the very end.

## why
[[principle-09-git-sovereignty]] says git is sovereign - which is about not *performing*
git operations, not about treating repo state as a precondition for work. inverting it
into a blocker stalls the build for something he never asked for, and burns the autonomy
he granted at sanction ([[principle-10-autonomy-after-sanction]]). he is explicit that
the division of labour is: agent does the fixes, he does the record. the same shape recurs
outside git, too - a slow or timing-out sub-task is not a blocker either, same card, generalised.

## how to apply
- work straight through irreversible-looking steps that he already sanctioned. if he said
  "delete X", the harvest being safe LOCALLY is enough; a push is not a precondition.
- keep a running list of git actions and emit it once, at the end, as copy-pasteable lines.
- when the repo state genuinely changes what the code must do (a public repo means secrets
  cannot be committed), fix the CODE and mention it - do not convert it into a stop.

## verbatim tells
- "do not commit anything ever"
- "yes dont commit anything ever, thats my job. you just do the fixes and give review at end"
- "stop worrying about git operations? i told you i git commit and add and whatnot, please
  just continue brain traversal and give git instructions at end. i already told you this"

## anti-pattern that drew heat
declaring "BLOCKER FOR YOU: create the private remote" and halting phase 0b on it, twice,
after being told the division of labour. the deletions were already sanctioned and the
harvest was already verified on disk; nothing about a missing remote made them unsafe.
