---
name: principle-45-scope-is-the-ask
kind: principle
rule: a sanctioned change does what was asked and stops. adjacent cleanup nobody asked for is not a bonus - it is what turns a two-step task into a review loop, because the gate then reviews the widened surface.
interest: [intent-efficiency, intent-control]
confidence: high
evidence_count: 1
binds: [code]
tells: ["this should have just been moving main fn's so i dont see the big confusion", "what was my original ask again?", "how much more is left?"]
---

# P45 - the scope of a change is the ask, not everything nearby

## rule
when he sanctions a change, the deliverable is that change. work that is genuinely IMPLIED
by it is in; work that merely became visible while doing it is out - name it and move on.

the test is mechanical: **could the ask be satisfied without this edit?** if yes, it is a
separate pass, and it needs its own sanction.

- implied, therefore in: naming a constant so a `@param` has something honest to point at;
  correcting a doc that describes the layout the change just replaced
  ([[principle-37-comment-the-artifact-not-the-edit]]).
- adjacent, therefore out: renaming his existing constants to a nicer convention, re-cutting
  separator widths, aligning trailing-comment columns, fixing pre-existing content errors
  in files the change never touched.

## why
he asked to move `main()` back into ten CUDA lab files and add `@param` blocks. the move
itself was one pass. the sprawl came from unrequested extras - a `BS`->`BLOCK` rename,
separator re-cutting, column alignment - and then the cold gate reviewed that widened
surface: 11 of its 21 first-round findings were nits about the cosmetics that were added on
initiative, not about the work he asked for. he read the loop and said so:

> "this should have just been moving main fn's so i dont see the big confusion"
> "what was my original ask again?"

the cost is not the extra edits, which were harmless. the cost is his attention: a task he
scoped as two steps came back as two review rounds and 52 findings ([[intent-efficiency]]),
and he had to ask what his own request had been to re-anchor it ([[intent-control]]).

## how to apply
- restate the ask in one line before starting, and keep it visible. every edit answers to it.
- when a genuine improvement surfaces mid-task, do NOT take it. write it down, finish the
  ask, and hand him the list as its own decision. he welcomes big refactors
  ([[principle-20-refactors-welcome]]) - as a sanctioned task, not as a rider on another one.
- the widened surface is what the gate measures. scope discipline is what makes the gate
  terminate ([[principle-03-review-gate]]).
- this does NOT license leaving the ask half-done, and it does not override the doc-accuracy
  rules for text the change itself authored: once a comment is re-typed into a new doc block,
  it belongs to the change and its claims must be true ([[principle-04-anti-fabrication]]).

## orthogonality
[[principle-14-minimal-surface]] bounds the ARTIFACT (no dep or abstraction it does not need).
P45 bounds the CHANGE (no edit the ask does not need). a minimal artifact can still be reached
by a sprawling diff, and that diff is the thing he had to sit through.
[[principle-20-refactors-welcome]] says a big refactor is welcome; P45 says it is welcome as
its own sanctioned unit.

## anti-pattern
"while I was in there I also..." on work he did not sanction. shipping a rename, a reformat
and a convention change stapled to a two-line fix, then presenting the gate's findings about
that extra surface as if they were findings about his request.
