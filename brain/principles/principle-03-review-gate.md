---
name: principle-03-review-gate
kind: principle
rule: Gate every phase with a cold, independent, multi-lens review. Wait for ALL reviewers, converge, ADJUDICATE each finding against the artifact's contract, then fix every surviving nit - even a single-agent one - before advancing.
interest: [intent-trust, intent-craft]
confidence: very-high
evidence_count: 25
tells: ["triple review first", "COLD/UNGUIDED", "even smallest nits", "dont skimp out because youre lazy", "find ANY remaining issues or nits or large bugs"]
---

# P03 - Review-gate every phase (cold, independent, converged)

**Rule.** Between phases, run an independent review. His exact protocol:
1. Review the **git diff between phases COLD / UNGUIDED** - prompt reviewers with no
   leading context: *"check git diff btwn X and Y and surface as many issues as you have,
   biggest bugs to smallest nits, be thorough."*
2. **Barrier, then converge.** ALL N reviewers must return before anything is fixed. Fixing
   on `[1, N-1]` mutates the tree reviewer N is still reading, and its findings come back
   describing a file that no longer exists.
3. **Adjudicate, then fix.** A finding is **evidence, not a verdict**. Classify each against
   the artifact's stated contract - valid / invalid / deferred-to-a-later-phase - and fix
   only the survivors. Every surviving nit gets fixed, including one raised by a single
   reviewer. A rejected finding is logged with its reason, never silently dropped.
4. **Dispatch only the reviewers that are relevant - but never skimp.** "you dont need to
   dispatch ALL ... JUST what you think is necessary. however, dont skimp out on it
   because youre lazy, it must be thorough."

## The dispatch roster (which agent, when, and does it WRITE?)

Regardless of language, every implementation gets all three passes:

| when | agent | mode |
|---|---|---|
| **before** (to shape the plan) | semantic-architecture-reviewer | reads; its findings feed the plan |
| **after** (cold, did it land right?) | semantic-architecture-reviewer | reads; dispatched on the finished diff |
| **in-post** (last, after correctness) | the `aav-style-*` suite (any language) | **EDITS** |

**The style agents are EDITORS, not reviewers.** They modify files. Dispatch them only
when you intend the edits to be made - never to "get a styling opinion." Using them as a
read-only lens is a category error, and it puts writers on the tree during a review, which
breaks the freeze rule above.

**The main agent adjudicates.** The cold agents produce evidence; deciding which findings
are appropriate to implement is the main agent's call under step 3 - a cold reviewer does
not get a commit bit on judgement.

**Why.** He does not trust a single confident pass ([[intent-trust]]); independent
adversarial review is how correctness and architectural integrity get verified ([[intent-craft]]).
The "dispatch X reviewer" position is really the interest *"verify this independently so I
can trust it without reading every line."*

**How to apply.**
- Cold prompts. Don't tell the reviewer what you think is wrong - let it find it.
- The first feedback pass may be remediated by a worker; then re-review.
- "do the triple review first, then fix, then the fmt and style" - order matters:
  correctness/architecture review -> fix -> style/fmt last.
- Reviewers must not **invent** issues ([[principle-04-anti-fabrication]]): "remember not
  to make up issues, but also be heavily scrutinizing line by line."
- **Freeze the tree under a live review.** A review is a measurement, and a measurement of a
  moving target is noise. While any reviewer is running, nothing mutates the tree - no
  worker dispatch, no edit. A writer launched 29s after a background review once made it
  report a red suite that was green, and blame the diff under review.
- **State the artifact's contract in the dispatch.** Cold means blind to the *author's
  framing*, not to what the thing IS. A tutorial whose deliverable is `todo!()`, or phase 3
  of an 8-phase plan, must say so, or the reviewer's default prior fires and it blocks on a
  property the artifact has on purpose ([[principle-29-interrogate-the-work]]).

**Anti-pattern.** Skipping the gate, a warm/guided review that only confirms your own
work, or dropping a single-reviewer nit because "it's minor." **And the inverse, which is
just as bad:** treating every finding as golden and remediating an invalid one. "This is
incomplete" against a deliberately-incomplete artifact is a loop that cannot terminate -
fixing it destroys the thing the artifact was.
