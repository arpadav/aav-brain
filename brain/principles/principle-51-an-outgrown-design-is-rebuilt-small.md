---
name: principle-51-an-outgrown-design-is-rebuilt-small
kind: principle
rule: when a build has grown far past his stated steps and every review round still finds more, the design is the defect, not the diff. measure the size against his own step list, then rebuild small from his canonical statement - harvesting the edge cases the old code learned - instead of patching another round.
interest: [intent-craft, intent-efficiency, intent-comprehension]
confidence: medium
evidence_count: 5
tells: ["many bugs = bad design, so go bsck to a plan/design phase", "why is it 16 massive modules for this simple 4 stages", "has this been over-engineered? its taken like 2-3 weeks to get this working, would a shell script have been easier in some places? be completely honest", "its 30k lines and constantly finding issues", "i need you to make and execute a seperate plan. in your own workspace or worktree, i want you to do a complete refactor of this to reduce the lines of codes", "it just seems like so much went into this but the initial design was bad", "yes its not perfect and might be a bit spaghetti, but the general gist and edge cases which i havent described should be accounted for", "if anything in the repo *disagrees* with the 1-4 i described, it is wrong and 1-4 is canonical and true", "learn from this bad design and see where the faults always keep happening", "they think its TOO simple with the balena device ssh, its more complex than that", "this should not be 1/7... i thought this was a simple cut to remove?"]
tension: [principle-14-minimal-surface]
---

# P51 - an outgrown design is rebuilt small, not patched

## rule
his step list is the yardstick. `hml deploy` was four steps (find the onnx, find a device, trtexec, write the
artifacts) and became 13.5k lines plus 10.9k of tests, then drew 22, 36, 40, 22 findings across five gates on a
450-line change. that is not a review backlog; it is a design verdict. stop gating, go back to the design phase,
and rebuild small from his statement of the problem.

## why
[[intent-craft]]: many bugs = bad design, in his words - a design that keeps producing issues is wrong at the root,
and each patch round buys the next one. [[intent-efficiency]]: weeks of remediation cost more than a rewrite
bounded by the steps he named. [[intent-comprehension]]: he must be able to read the result; 16 modules for 4
stages cannot be read. he also noticed the brain only agreed it was over-engineered when HE asked - the proportion
check is the agent's job to run first (see [[principle-14-minimal-surface]], which bounds the artifact, where this
card says what to do once it is already over-built).

## how to apply
- **proportion first**: set the line count beside his step list before the plan, and again when a gate loop climbs.
  finding counts that do not drop across two rounds are the trigger ([[principle-03-review-gate]], bound the loop).
- **his statement is canonical**: where the old code disagrees with the steps he described, the code is wrong. the
  rebuild is a spec-driven rewrite, not a port ([[principle-20-refactors-welcome]] covers the welcome).
- **harvest before cutting**: he told it to learn the logic, not copy the structure. mine his claude history for the
  faults that keep recurring, his shell history for how the tool is really invoked, and the old tests as a list of
  behaviours and edge cases. keep what earned its place in a failure; drop machinery that exists only for the
  abstraction (a framing layer, a mirror/offline road, a typed exception per sentence).
- **small is not naive**: a 60-100 line shell script was the previous agent's answer, and he said it undersold the
  balena ssh case - "its more complex than that". both bounds hold: not thousands of lines, not a script that forgets
  the hard part. the hard part gets exactly its own lines.
- **language is a free choice per layer** ("not only python"): orchestration where the logic and the rules live,
  plain sh where the thing runs on the device. the implementer is [[principle-23-standing-decisions]]'s, never
  python-pro.
- work in a separate worktree so the result arrives as one small diff against main for his approval
  ([[principle-09-git-sovereignty]]); the old head stays tagged.
- the gate for a rebuild of device code is a live run ([[principle-52-device-facing-code-is-gated-by-a-live-run]]).
- **it applies at phase scale too, and the first check is whether the thing is even consumed.** a "make the cli
  installable without torch" phase grew a shared lazy re-export helper (+373/-193, 21 gate findings, most on the
  helper's edges). he asked "i thought this was a simple cut to remove?" - one grep showed nothing used the
  re-exports, and emptying three `__init__`s did the job (+168/-119). before building machinery to preserve a
  surface, grep for its consumers.
- **when a gate's findings concentrate in one artifact round after round, cut that artifact.** a changelog install
  recipe drew findings two gates running while the ci job doing the same install was tested; replacing the prose
  with a pointer to the job ended it.

- **at gate scale it is the DESIGN state.** `brain-gate.py round` sends a non-dropping count there:
  map the flow and dependency graph, split hard from soft requirements, regroup (merge, split,
  reorder, cut), propose once with the counts, and accept only on a net decrease at the re-review.

## anti-pattern
patching a fifth gate's findings on the same machinery; accepting "just a shell script" as the whole answer and
dropping the edge cases the old code paid for; porting the old module layout under new names.
