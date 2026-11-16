---
name: principle-74-the-last-review-runs-at-high-effort
kind: principle
tier: conditional
rule: the final full review before a PR, and a replan he calls because he fears something was missed, run at HIGH effort - never medium. dispatch the cold review (and the re-plan) with the effort set explicitly, and when he asks for "one last full review of everything" it is the whole change, not the diff since the last gate.
interest: [interest-trust, interest-comprehension]
confidence: medium
evidence_count: 2
tells: ["i thought you were on high effort, i need one last full review of everything... medium doesnt cut it. sorry. one last cold review with high effort", "hey can you replan with high effort ? you were on medium and im afraid some stuff was missed...."]
---

# P74 - the last review runs at high effort

## rule
the closing review of a build, and any replan he asks for out of doubt, run at high effort. a
medium-effort pass that finds little is not evidence the change is clean; he reads it as a pass
that missed things, and spends a round re-asking.

## why
the last review is the only one between the work and the PR ([[principle-03-review-gate]]); its
depth is the thing he is buying. cheap depth there costs him the round trip it was meant to save.
this is the closing exception to [[principle-53-review-size-follows-the-change]], which sizes
per-phase gates: the final one is not sized down.

## how to apply
- set the effort on the dispatch itself; do not inherit a lower session default.
- the scope is the whole branch against its base, after the PR text, the magic numbers and the open todos he named are done.
- do not announce it as done on a medium pass and offer to redo it.
