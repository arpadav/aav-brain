---
name: principle-33-git-is-not-a-blocker
kind: principle
rule: never treat git state as a blocker or a gate. he commits, adds, and pushes - the agent does the fixes and reports git instructions at the END. do not stop, do not ask, do not invent a gate out of repo state.
interest: [intent-sovereignty, intent-efficiency]
confidence: very-high
evidence_count: 3
tells: ["do not commit anything ever", "thats my job. you just do the fixes and give review at end", "stop worrying about git operations?", "please just continue", "i already told you this"]
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
- DO collect the git actions and hand them over as instructions at the very end.

## why
[[principle-09-git-sovereignty]] says git is sovereign - which is about not *performing*
git operations, not about treating repo state as a precondition for work. inverting it
into a blocker stalls the build for something he never asked for, and burns the autonomy
he granted at sanction ([[principle-10-autonomy-after-sanction]]). he is explicit that
the division of labour is: agent does the fixes, he does the record.

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
