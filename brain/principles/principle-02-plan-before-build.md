---
name: principle-02-plan-before-build
kind: principle
rule: Produce a small-but-verbose plan with a concrete usage example before writing code; write it to plans/.
interest: [intent-comprehension, intent-control]
confidence: very-high
evidence_count: 39
tells: ["make a plan", "jumping off point", "keep this SMALL but verbose", "write an example struct so i can see it visually"]
---

# P02 - Plan before build (small, verbose, with a worked example)

**Rule.** Non-trivial work starts with a plan. The plan is **small in scope but verbose
in detail**, includes a **concrete worked example** (a struct using the proposed API, a
sample invocation, a tiny flowchart), and is **written to `plans/`** on disk so it is
reviewable and reversible. He used `/plan` 39 times - plan mode is his default entry.

**Why.** He learns by concrete instance and won't commit to an abstraction he can't see
([[intent-comprehension]]). The plan-on-disk is also a control surface: it makes the
decision explicit and the path cheap to change ([[intent-control]]).

**How to apply.**
- Scope tight: "a jumping off point ... something i can get my hands dirty with before
  committing." Don't over-architect the first plan.
- Always include a **visual/worked example** of the new API in use, with comments.
- Persist it: write to `plans/NN-name.md`. Multi-phase work gets a phase index.
- Bake the **review-gate strategy into the plan itself** ([[principle-03-review-gate]]).
- Run the plan past architectural scrutiny BEFORE presenting/executing it.

**Verbatim tells.**
- "read PLAN.md and make a plan for a jumping off point. keep this SMALL but verbose"
- "write an example of a struct which uses all of the new proposed api, so i can see it
  visually, and describe how it would work with comments and flowchart"
- "make a multi-phase plan. add to the plan a review-gate strategy which uses ... agents"

**Anti-pattern.** Jumping straight to edits on a non-trivial task; an abstract plan with
no example he can hold.
