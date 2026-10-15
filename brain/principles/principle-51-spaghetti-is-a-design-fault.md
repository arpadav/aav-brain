---
name: principle-51-spaghetti-is-a-design-fault
kind: principle
tier: conditional
rule: when every available fix makes the code worse, or the valid-finding count stops dropping across review rounds, the DESIGN is the defect and the patch is not. leave the impl loop for DESIGN, measure the build against his own step list, and redesign that ONE atomic part from his canonical statement - harvesting the edge cases the old code learned. destructive and drastic proposals are sanctioned there, because a good design fixes the symptoms as a side effect.
interest: [intent-craft, intent-comprehension, intent-efficiency]
confidence: high
evidence_count: 7
binds: [code]
tension: [principle-14-minimal-surface]
tells: ["if there is spaghettificstion of code, then the DESIGN is faulty", "a good design will naturally fix issues, as a side effect of being a good design, rather than having agents just patch work", "ITS OKAY TO MAKE DESTRUCTIVE/DRASTIC suggestions", "hold up wtf?", "get OUT of impl and back to design/plan", "many bugs = bad design, so go bsck to a plan/design phase", "why is it 16 massive modules for this simple 4 stages", "has this been over-engineered? its taken like 2-3 weeks to get this working, would a shell script have been easier in some places? be completely honest", "its 30k lines and constantly finding issues", "i need you to make and execute a seperate plan. in your own workspace or worktree, i want you to do a complete refactor of this to reduce the lines of codes", "it just seems like so much went into this but the initial design was bad", "yes its not perfect and might be a bit spaghetti, but the general gist and edge cases which i havent described should be accounted for", "if anything in the repo *disagrees* with the 1-4 i described, it is wrong and 1-4 is canonical and true", "learn from this bad design and see where the faults always keep happening", "they think its TOO simple with the balena device ssh, its more complex than that", "this should not be 1/7... i thought this was a simple cut to remove?"]
---

# P51 - spaghettification is evidence the design is wrong

## rule
a reviewer's finding is evidence about the code. a finding whose only honest fixes all make
the code **worse** is evidence about the DESIGN. those are different defects and they have
different repairs: the first is a patch, the second is a subdesign.

the tell is mechanical, and it is not "this feels messy":

- **every fix you can name adds a branch, a flag, a parameter, or a special case.** none
  removes one.
- **the same seam keeps producing findings round after round**, each one different, none of
  them the last.
- **the fix has to know about something it should not** - a formula reaching for a wire
  field, an error type carrying a caller's concern, a leaf importing the root.

any one of those means: stop patching. the machine has a state for this - ADJUDICATE emits
`design_fault` and the walk goes to DESIGN, whose whole scope is ONE atomic part. a review count
that does not drop across rounds (`brain-gate.py round` -> `not_converging`) reaches the same state.

his step list is the yardstick. `hml deploy` was four steps (find the onnx, find a device, trtexec, write the
artifacts) and became 13.5k lines plus 10.9k of tests, then drew 22, 36, 40, 22 findings across five gates on a
450-line change. that is not a review backlog; it is a design verdict. stop gating, go back to the design phase,
and rebuild small from his statement of the problem.

## why
a good design fixes issues as a SIDE EFFECT of being a good design. that is the whole reason
to have one, and it is why patching around a bad one never converges: each patch is honest
work that makes the next finding likelier ([[intent-craft]]). the cost lands on him - he has
to read a growing artifact to keep his model of it, and a design nobody redesigned is a model
nobody can hold ([[intent-comprehension]]).

the machine made it unavoidable. REMEDIATE's own doc said it "does NOT leave the impl phase",
so no finding could ever be ruled a design fault - every one became a patch, and the next
round's findings were about the patch. he stopped it by hand:

> "hold up wtf?"

[[principle-20-refactors-welcome]] already NAMED this anti-pattern - "timidly patching around
a design flaw instead of fixing the design" - and had nowhere to route it, which is how a
correct card watched it happen. the file sizes that ended that build are recorded once, under
[[principle-27-organization-reorg]]'s `## the measurement`. they are evidence that the tree
was never looked at; they are NOT independent evidence for this card's cause, and citing them
twice for two different causes would be exactly the failure both cards are about.

[[intent-craft]]: many bugs = bad design, in his words - a design that keeps producing issues is wrong at the root,
and each patch round buys the next one. [[intent-efficiency]]: weeks of remediation cost more than a rewrite
bounded by the steps he named. [[intent-comprehension]]: he must be able to read the result; 16 modules for 4
stages cannot be read. he also noticed the brain only agreed it was over-engineered when HE asked - the proportion
check is the agent's job to run first (see [[principle-14-minimal-surface]], which bounds the artifact, where this
card says what to do once it is already over-built).

## how to apply
- **scope is the PART, never the plan.** the error model. the id scheme. the one seam the
  findings keep circling. a subdesign that reaches for a second part is a re-plan, and
  re-planning a sanctioned build is his call ([[principle-02-plan-before-build]]).
- **destructive and drastic are sanctioned here.** delete the layer. invert the ownership.
  collapse the two types into one. the size of the change is not an argument against it
  ([[principle-20-refactors-welcome]]); the only test is whether the result is more
  maintainable and more atomic.
- **write it to plans/ as an addendum before building to it**, so a cold reviewer reads the
  new shape as errata rather than as drift from the design it no longer matches
  ([[principle-02-plan-before-build]]).
- **then return to REMEDIATE** and fix the remaining findings against the new shape. the
  subdesign replaces the patch; it does not excuse the rest of the round.
- measure before you claim it: `brain-shape.py <repo>` puts numbers on the file lengths,
  folder fan-out and duplicated datatypes that usually accompany this
  ([[principle-27-organization-reorg]], [[principle-28-dry-merge-blast-radius]]).

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
- the gate for a rebuild of device code is a live run ([[principle-60-device-facing-code-is-gated-by-a-live-run]]).
- **it applies at phase scale too, and the first check is whether the thing is even consumed.** a "make the cli
  installable without torch" phase grew a shared lazy re-export helper (+373/-193, 21 gate findings, most on the
  helper's edges). he asked "i thought this was a simple cut to remove?" - one grep showed nothing used the
  re-exports, and emptying three `__init__`s did the job (+168/-119). before building machinery to preserve a
  surface, grep for its consumers.
- **when a gate's findings concentrate in one artifact round after round, cut that artifact.** a changelog install
  recipe drew findings two gates running while the ci job doing the same install was tested; replacing the prose
  with a pointer to the job ended it.
- **at gate scale it is the DESIGN state.** `brain-gate.py round` sends a non-dropping count there,
  and ADJUDICATE sends a design-fault verdict there: map the flow and dependency graph, split hard
  from soft requirements, regroup (merge, split, reorder, cut), and accept only on a net decrease at
  the re-review. within one part it proceeds; a regroup that reaches past one part is a re-plan and
  is put to him once, with the diagram and the counts.

## orthogonality
the big-structural-change family, kept distinct. [[principle-20-refactors-welcome]] is the
DISPOSITION - do not dodge a change because it is big - and it already named this anti-pattern;
P51 is the DIAGNOSIS and the ROUTE: three mechanical tells separating "the patch is wrong" from
"the design is wrong", and the ADJUDICATE -> DESIGN edge that gives the verdict somewhere to
go. P20 without P51 is a stance with no trigger; P51 without P20 is a trigger with no permission
to act on it. [[principle-27-organization-reorg]] is WHERE things live and
[[principle-28-dry-merge-blast-radius]] is collapsing duplication - both are frequent SYMPTOMS of
what P51 diagnoses, never the diagnosis itself.

## verbatim tells
> "if there is spaghettificstion of code, then the DESIGN is faulty"
> "a good design will naturally fix issues, as a side effect of being a good design, rather than having agents just patch work"
> "ITS OKAY TO MAKE DESTRUCTIVE/DRASTIC suggestions if this significantly improves design and reduces spaghettification"

## anti-pattern
adding the eighth flag to a function whose seven flags were each added the same way, and
reporting the round converged. and its opposite: calling every finding a design fault, which
is how a bounded remediation becomes an unbounded redesign - the tell is specific
([[principle-04-anti-fabrication]]), and without it you do not have one.

patching a fifth gate's findings on the same machinery; accepting "just a shell script" as the whole answer and
dropping the edge cases the old code paid for; porting the old module layout under new names.
