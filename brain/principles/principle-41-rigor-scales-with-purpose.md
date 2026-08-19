---
name: principle-41-rigor-scales-with-purpose
kind: principle
rule: how hard to enforce idiom is set by what the artifact is FOR. a scratch or testing workspace - skip it. an ephemeral tutorial - adhere lightly, do not be anal. production - be extremely attentive and exhaustive. ask the purpose before writing; never infer it from the code.
interest: [intent-efficiency, intent-craft]
confidence: very-high
evidence_count: 3
binds: [code]
tells: ["if this is a testing workspace, ignore all", "if its a tutorial sort of workspace which is ephemeral, then adhere a bit, dont be super anal", "if its production code, be extremely attentive and exhaustive", "the whole point is that each approach is completely standalone", "i wanted that duplication on purpose"]
---

# P41 - rigor is a function of purpose

## rule
the standards are not uniform across artifacts, and applying the strictest one everywhere is itself a
failure. three registers:

| purpose | idiom enforcement |
|---|---|
| **scratch / testing workspace** | skip it. the artifact exists to answer a question and then die. |
| **ephemeral tutorial / learning** | adhere lightly. readable and consistent; not exhaustive, not anal. |
| **production** | extremely attentive and exhaustive. every rule in the catalogue, every instance. |

purpose is ASKED at the start, never inferred. code cannot tell you what it is for.

## why
over-applying craft costs more than it returns ([[intent-efficiency]]) and actively destroys some
artifacts. a seven-variant CUDA teaching suite exists precisely so each variant can be read alone;
"library-fying" the shared geometry across them deleted the thing it was for - "the whole point is
that each approach is completely standalone... i wanted that duplication on purpose." the same
extraction in production code is [[principle-31-libraryfy-shared]] and correct. the rule did not
change; the purpose did.

conversely, under-applying it in production is what forces a large refactor later, which is the cost
[[principle-40-idiom-needs-exemplars]] exists to avoid.

## how to apply
- purpose is question 0 at intent, before the plan ([[principle-01-no-assumptions]]). a missing
  answer is a question, not a default.
- scratch -> simplest thing that runs. duplication is free. do not anticipate a future caller.
- tutorial -> optimise for reading one file in isolation. deliberate duplication is often the POINT;
  do not merge it.
- production -> the durable structure, the shared primitive, the full catalogue, exhaustively.
- the register applies to IDIOM and STRUCTURE. it never licenses fabrication, an unread error, or a
  skipped verification - [[principle-04-anti-fabrication]] does not scale with purpose.
- when the purpose changes mid-flight (a scratch tree being promoted), re-ask rather than silently
  raising the bar.

## orthogonality
[[principle-40-idiom-needs-exemplars]] says WHAT the idiom rules are and in what form they bind; P41
says HOW HARD to apply them here. [[principle-28-dry-merge-blast-radius]] says merge a real DRY
violation regardless of blast radius - P41 is what decides whether duplication in this tree IS a
violation or is the deliverable. [[principle-14-minimal-surface]] is about how much API to expose;
this is about how much rigor to spend.

## anti-pattern
applying production instincts to a scratch tree - the failure that produced a `common/` package of
shared headers in a workspace built for standalone variants, and drew heat for it. also its mirror:
shipping production code at scratch rigor and calling the cleanup a refactor.
