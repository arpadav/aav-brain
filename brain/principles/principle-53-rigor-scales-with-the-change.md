---
name: principle-53-rigor-scales-with-the-change
kind: principle
tier: conditional
rule: how much review a change buys is set by what the CHANGE did, not by a phase ending. a patchwork fix is proved by the mechanical check and its own acceptance clause; the cold multi-lens review is for architectural change and a lot of moved code. measure the change and take the exit the measurement names.
interest: [intent-efficiency, intent-trust]
confidence: high
evidence_count: 3
tells: ["no review gates here on documentstion dude, just on code", "do NOT do a full cold review gate on something which is clearly just a patchwork fix", "this is ONLY when architectural changes are required and a lot of code has been changed", "adding a single flag to some struct can just be checked with built test lint etc", "no... thats not necessary"]
---

# P53 - the cold review is bought by the change, not by the calendar

## rule
a phase ending does not buy a cold multi-lens review. the SIZE and KIND of what the phase changed
does. two exits, and the measurement picks one:

| what changed | what proves it |
|---|---|
| a flag on a struct, a corrected number, a renamed local, a typo | the mechanical check + the task's own acceptance clause |
| a type moved between modules, a signature its callers depend on, a new door, money / authorization / an audit trail | the cold multi-lens review |

the budget is a NUMBER, not a judgement made fresh each time - the same reason
[[principle-27-organization-reorg]] has thresholds instead of the adjective "too long".
`brain-gate.py phase` scores the change (code lines, plus a weight per added, deleted or renamed
file; prose scores nothing) and prints `gate N` or `defer`. under it, the change still gets
verified and styled; it just does not commission reviewers. a ref git cannot resolve stops the
script with a usage error - that is never a `defer`.

**small changes accumulate; they do not each dodge the review.** brain-gate.py keeps the pending
score per checkout from the last review that ACTUALLY RAN, so two deferred phases are measured
together with the third. `--last` on the final phase gates whatever is still pending.
`brain-shape.py --since` is a second, cruder budget kept beside it while
plans/open-items/G01-two-gate-arming-checks.md is open; where they disagree, brain-gate.py wins.

**KIND overrides size in one direction only.** a two-line change to an authorization door is ARMED
- tag its phase `L` and the plan's expected size outranks the small diff. a thousand lines of
prose is not. size can promote, it can never demote.

## why
the review used to cost the same whether the phase was thousands of new lines or two lines of
formatter appeasement, so the same machinery reviewed both and the review budget went where the
phases were rather than where the risk was ([[intent-efficiency]]). measured over one build: 103
reviewer dispatches whose cadence tracked phase boundaries, a one-file phase getting the same
five-lens treatment as a 288-file one.

it also costs trust in the other direction. a gate that fires on everything is a gate nobody reads
carefully, and the findings that matter arrive in the same list as the ones that do not
([[intent-trust]]).

## how to apply
- measure at the boundary; do not eyeball it. announce which exit the measurement named.
- under budget is not "skipping the gate" - it is a measurement with a spoken verdict, which is what
  [[principle-35-gates-are-agent-side]] asks for when it says a phase too small to gate must SAY so.
- a remediation is a change like any other: it re-enters the loop and is re-measured, never waved
  through because a review already looked at the thing it fixes.
- the rounds are bounded by `brain-gate.py round`: two per gate. a round-2 decrease is fixed and
  verified with no third review; no decrease goes to DESIGN ([[principle-51-spaghetti-is-a-design-fault]]).

## documentation never buys a cold gate
user-facing documentation (a book, a guide) gets the mechanical checks (build, the page checker,
the examples run, screenshots looked at) and his own read - never a cold multi-lens review gate.
code keeps its gates. evidence (tinyklv book2, 2026-10-14): three gate rounds on doc infra and pilot
pages surfaced ~100 edge cases and burned large token budgets. his words: "stop the gate thats a
waste of tokens ... no review gates here on documentstion dude, just on code".

## orthogonality
[[principle-41-rigor-scales-with-purpose]] sets rigor by what the ARTIFACT IS FOR - scratch,
tutorial, production - and is answered once at intent. this sets it by what THIS CHANGE DID, and is
answered at every boundary. a production repo is P41-maximum forever and still does not buy a cold
review for a one-line fix. [[principle-03-review-gate]] is what the review does once it is bought.

## anti-pattern
a full cold review commissioned for a stale number in a doc comment. and its mirror, which is worse:
reading this card as permission to skip the review on a change that moved a type or touched money
because the diff looked small.
