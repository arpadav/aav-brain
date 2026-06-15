---
name: brain-review
description: "Cold, unguided, multi-lens review of the current diff, as Arpad would gate it. Load this when he says 'review this', 'review the diff', 'find any issues/nits', 'triple-review', or wants a pre-merge sweep. A user ENTRY skill: it enters the flow at REVIEW (regime ask-first), dispatches the cold review-gate agent, and hands the walk to brain-meta-drive - which rides the SHARED PHASEGATE -> REMEDIATE -> VERIFY rails (converge findings, fix, verify) to a terminal."
---

# brain-review: cold multi-lens review of the current diff, as arpad

the review entry. he says "review this" and this skill runs his review gate: a COLD, unguided,
biggest-bug-to-smallest-nit pass by independent reviewers, converged, with even single-lens nits
blocking. it does NOT walk the flow by hand - the walk is `brain-meta-drive`'s job. this entry only sets
the start node and the ask-first regime; the engine reuses the same gate machinery a build uses.

## setup (run first - discover the brain, no hardcoded path)
```bash
eval "$(brain-find --export)"   # sets $AAV_BRAIN
```
read `$AAV_BRAIN/brain/CONSTITUTION.md`.

## 1. set the entry
- `$STATE` = `REVIEW` (the cold-review node).
- `$REGIME` = `ask-first` (review never crosses SANCTION; it asks before it remediates - it does not
  auto-fix his tree without a nod).

no reconstruction needed: the artifact under review is the current working diff, which is on disk.

## 2. hand the walk to the engine
load `brain-meta-drive` and run its trampoline from `REVIEW`. it dispatches the cold `brain-review-gate`
agent (a fresh, cleared-context pass that never saw the author's framing - P03/P04), then funnels into
the SHARED `PHASEGATE -> REMEDIATE -> VERIFY` loop: converge the findings, fix even a single-lens nit,
re-review, verify, to a terminal. the review region adds NO new transitions on those shared states - it
just enters them.

## 2b. the would-arpad pass (a SUPERPOSITION on the cold gate, P29)
the cold gate above is only HALF of a brain review. it has no brain memory by design. so, INDEPENDENTLY
and after it, run a second brain-guided pass on the same diff - this is the superposition, not a
replacement, and the cold pass is never warmed by it:
- recall the cards the diff touches: `python3 $AAV_BRAIN/bin/brain-recall.py "<what the diff changes>"`.
- with that memory loaded, interrogate the diff at EVERY granularity - "would arpad write THIS file
  like this? this folder structure like this? this individual function like this?" (P29). a "no" is
  binding only with a reason - cite the card it violates.
- this is DISTINCT from the programming-style pass (brain-meta-style: trim/format/docs). here the
  question is whether he'd have written it this way AT ALL, not how to tidy it.
- converge would-arpad findings INTO the same gate: a would-arpad nit blocks advancement exactly like
  a cold-lens nit (P03 - even a single-source nit is binding). correctness -> fix -> style/fmt last.

## stops
a transition to a `blocked`/ASK state is the only sanctioned pause: cross back and ask via
brain-meta-intent. a gate below threshold routes BACK (to REMEDIATE), never forward - dont advance dirty.

## reporting
only at gates, and only what he cant see himself: the converged verdicts, the blocking nits, the single
next action. no diff recaps. lowercase, terse, ends on the next action.

## hard rules
never fabricate a finding. correctness -> fix -> style/fmt last. never commit/push unless told. never
trample his manual edits.
