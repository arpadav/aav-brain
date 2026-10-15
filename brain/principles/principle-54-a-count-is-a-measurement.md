---
name: principle-54-a-count-is-a-measurement
kind: principle
tier: conditional
rule: a count written in a document is a measurement with a timestamp, not a claim that can be wrong. when it disagrees with the tree, re-measure, correct the number, and move on in one clause. it is never a finding, never an incident, and never a reason to commission a review.
interest: [intent-efficiency, intent-trust]
confidence: high
evidence_count: 3
tells: ["stop being so hardstuck on mismatched numbers", "a human would just recognize the doc is out of date", "a damn doc comment says 101 pub items but the agent counted 103, so holy shit i need to fix this asap and review gate!... no", "thats not necessary"]
---

# P54 - a stale number is a re-measure, not an event

## rule
a doc block saying "101 public items" over a crate that now has 103 is not a defect, a regression,
or a contradiction. it is a measurement someone took at a moment that has passed. re-run the count,
write the new one, move on. **one clause in the report, and no more.**

this binds three places:
- **a reviewer** does not raise it as a finding.
- **an adjudicator** classifies it invalid-as-a-finding and fixes the number in passing.
- **a worker** that trips over one corrects it inline and does not escalate.

**a count SCOPES the task that cites it**, though - so re-run the census before acting on a task
whose ask is stated in terms of a number, or you will do 101 items of a 103-item job.

## why
the alternative is what actually happened, repeatedly: a number mismatch treated as a live defect,
which buys an investigation, a remediation round, and sometimes a cold review - all to change one
integer. the cost is not the fix, it is the machinery the fix summons ([[intent-efficiency]]).

and it corrodes the finding list. when a stale integer arrives in the same report as a money-movement
bug, the report stops being a ranking ([[intent-trust]]). a human reading the doc would recognise it
as out of date and keep going; the brain must do the same.

## how to apply
- re-measure FIRST. the doc is not automatically the wrong one - sometimes the tree regressed, and
  that IS a finding.
- correct the number in the same diff as whatever you were already doing. it does not get its own
  commit, its own task, or its own round.
- generated counts belong to their generator: if a number is regenerable, regenerate it rather than
  hand-editing, and if nothing regenerates it, that absence is the real finding.
- the same reading applies to any measurement carried in prose - a timing, a file count, a percentage.

## orthogonality
[[principle-53-rigor-scales-with-the-change]] says a small change does not buy a cold review; this
says one particular class of "finding" is not a change at all. [[principle-04-anti-fabrication]] is
untouched: correcting a stale number is not softening a report, and inventing a count you did not
run is still fabrication.

## anti-pattern
escalating an integer. also its mirror: leaving a number you KNOW is wrong because "it is only a
doc" - the fix is one clause, so there is no excuse for either failure.
