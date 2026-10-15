---
name: principle-50-the-standing-mission
kind: principle
tier: narrow
rule: every worker carries the END GOAL of the run, not only the phase's ask. work that exceeded the ask but moved the sanctioned mission is KEPT, never reverted for tidiness; work merely adjacent to the ask is not, and is not started either.
interest: [intent-craft, intent-efficiency, intent-control]
confidence: high
evidence_count: 2
binds: [code]
tension: [principle-45-scope-is-the-ask]
tells: ["slow down - the MAIN GOAL is to make this budget app", "if those edits are aligned with that goal, despite going above and beyond the original ask, then it is fine", "they did way too much! i need to revert this", "above and beyond"]
---

# P50 - the standing mission outranks the literal ask

## rule
a sanctioned run has a MISSION - build the budget service, make this crate idiomatic and
correct - and every task inside it is a step toward that mission, not a fence around it.
so the test a worker's extra work is judged by is not "was this in the sentence i was
given" but **"does this move the mission"**.

- moves the mission, therefore IN: a worker told "fix the two lines ruff is complaining
  about" that also makes the file idiomatic and in his voice, on a run whose mission IS
  making the code idiomatic.
- merely adjacent, therefore out: the same worker renaming his constants, re-cutting
  separators, or fixing content in files the mission never touches
  ([[principle-45-scope-is-the-ask]]).

**above and beyond does not mean MORE CODE.** it means more aligned with the end goal. a
worker that writes a speculative abstraction nobody asked for has not gone above and
beyond, it has gone sideways ([[principle-14-minimal-surface]]).

## why
reverting work that served the mission costs twice: the work, and then his attention to
undo the revert. it happened - a worker was dispatched for a lint fix on a refactor whose
whole point was idiom, delivered the idiom too, and the orchestrator read
[[principle-45-scope-is-the-ask]] and moved to revert it. he stopped that by hand:

> "slow down - the MAIN GOAL is to make this budget app, and right now this refactor to
> make things more idiomatic and correct. if those edits are aligned with that goal,
> despite going 'above and beyond' the original ask, then it is fine"

the brain had P45 and no counterweight, so the orchestrator applied the only rule it had.
serving [[intent-craft]] is the point of the run; spending his turn on a revert that
un-serves it is the opposite of [[intent-efficiency]].

## how to apply
- **every dispatch names the mission**, one line, above the task
  ([[principle-40-idiom-needs-exemplars]]: a worker cannot align to a goal it was not
  told). the brain-meta-author-prompt skill owns that line, and it is
  not optional on a multi-phase run.
- **when a worker exceeds the ask, adjudicate it against the mission before touching it.**
  aligned -> keep it, say so, move on. not aligned -> name it and revert only that part.
  never revert the whole delivery because part of it was extra.
- **the mission is what was SANCTIONED, never what you inferred.** if you cannot state it
  in one sentence from the plan or from his words, you do not have one - ask
  ([[principle-01-no-assumptions]]).

## orthogonality
[[principle-45-scope-is-the-ask]] is about the SURFACE a change presents to the gate: a
change that drags in unrequested cosmetics gets reviewed on the widened surface and burns his
attention on nits. that is still true, and P50 does not soften it. **the two divide by
DECISION, not by context, and the split is total:**

| | before the work | after the work |
|---|---|---|
| the question | should i take this on? | should i revert what was delivered? |
| the card | **P45.** could the ASK be satisfied without this edit? if yes, do not start it | **P50.** did it move the MISSION? if yes, keep it |
| the case | do not rename his constants while moving `main()` | do not revert an idiomatic pass on a run whose mission is idiom |

so on a run with a stated mission, a worker is scoped tightly by P45 going in AND its
delivered work is judged by P50 coming out. those are not in conflict: the worker keeps what
it built, and the NEXT dispatch is scoped tighter. with no stated mission there is nothing for
P50 to weigh against, and P45 governs both halves.

## verbatim tells
> "slow down - the MAIN GOAL is to make this budget app"
> "if those edits are aligned with that goal, despite going 'above and beyond' the original ask, then it is fine"

## anti-pattern
reverting delivered work because it exceeded the literal sentence, without asking whether it
served the run. and its mirror: pasting "go above and beyond" into a prompt and getting
volume - scope creep wearing the mission's clothes ([[principle-05-reuse-first]]).
