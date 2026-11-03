---
name: brain-execute
description: "Build a sanctioned plan to completion, as Arpad would - and RESUME it. Load this when he says 'execute', 'build it', 'go', OR 'continue' / 'keep going' / 'pick up where we left off' / 'resume'. A user ENTRY skill: it reconstructs where the build is, enters the flow at DOCTRINE (regime execute-through), and hands the walk to brain-meta-drive. If a build was cut off mid-phase, saying 'continue' just re-invokes this - it rebuilds state and walks from the current node to DONE. Stops ONLY on real post-sanction ambiguity. Prepares (never publishes) the commit."
---

# brain-execute: drive a blessed plan to completion (and resume it), as arpad

the build entry. he sanctions a plan and says "go" - or steps away mid-build and later says "continue" -
and this skill runs the rest: it figures out where the work is, then traverses the flow to DONE,
composing the meta-skills and dispatching the two cold agents. it does NOT re-plan and it does NOT walk
the flow by hand - the walk is `brain-meta-drive`'s job. this skill owns two things the engine does not:
**reconstruction** (where is the build?) and the **"continue" trigger** (resume without a new command).

## precondition
we are AFTER the sanction boundary: a plan exists in plans/ and he approved it. if no plan is sanctioned,
do NOT execute - switch to brain-plan.

## setup
read `$AVB/brain/CONSTITUTION.md`.

## 1. reconstruct state (this is the entry's job, NOT the engine's)
find the active plan in plans/; derive done-vs-remaining from the plan + git log/diff + the transcript.
use think-in-code for any large scan. do NOT ask him to re-explain what is on disk. from that, set:
- `$STATE` = the current flow node (a fresh build starts at `DOCTRINE`; a resumed one starts at whatever
  phase/gate the transcript + diff show was in flight).
- `$REGIME` = `execute-through` (this entry is post-sanction; autonomy is the default - run phases back
  to back, no needless pauses).

"continue" is just this skill re-invoked: it reconstructs `$STATE` again and resumes. that is why there
is no separate continue skill - resumption IS reconstruction.

## 2. hand the walk to the engine
load `brain-meta-drive` and run its trampoline from `$STATE` with `$REGIME`. it steps `flow.toml`,
recalls per state, dispatches each owner (a meta-skill or a cold agent), and loops the gates
(IMPL -> PHASEGATE -> VERIFY, looping through REMEDIATE) until each threshold holds - to DONE. you do not
re-implement that loop here.

handoff: with `$STATE`/`$REGIME` set and `$MODE` = `build`, call `Skill(brain-meta-drive)` and run `b-walk -s "$STATE" -m build` (paste the output) - the handoff contract lives in brain-meta-drive.

## how IMPL dispatches: fan out, then measure (P52)
you are the OVERSEER. you dispatch, you run the tree-wide command, you adjudicate, you commit -
you are not the one typing the code.

- **two to three workers at a time, issued as PARALLEL TOOL CALLS IN ONE MESSAGE.** one dispatch
  per message is a serial queue wearing a fan-out's clothes, and it looks identical in a transcript
  until you count them. each worker gets a file set no sibling touches, or its own worktree;
  disjointness is ARRANGED, never hoped for. stagger the refills - dispatch the next as one returns.
  the ceiling is the SESSION rate limit, shared by you and every subagent, which is why the number
  is three.
- **the tree-wide build/test/lint command is YOURS and runs ONE AT A TIME.** never a worker's. two
  builds on one target directory block on its lock; two mutation batteries over one checkout revert
  over each other's injection; a timing step measures a release binary that a second compile moves.
  a worker proves its own work with the cheap subset - format, lint, doc, the one crate it touched -
  in its own worktree.
- **tell every worker to COMMIT AS IT GOES**, and resume a killed one by message to its id rather
  than restarting it.
- the one time you stop dispatching is while a cold review is live: a review is a measurement and
  it freezes the tree, including your own edits (P03).

## the would-arpad self-check at IMPL (P29 - internal, NOT a pause)
as each phase generates artifacts, the worker interrogates its own output the way arpad would
([[principle-29-interrogate-the-work]]) - PRE: is this consumed, does it already exist, should i read
instead; POST, at every granularity: "would arpad write THIS file like this? this folder structure
like this? this individual function like this?" this is a SELF-check the worker runs and answers, not
a question back to him - execute-through holds (P10), do not pause to narrate it. it only becomes a
stop if the answer surfaces a genuine decision he'd want (then ask via brain-meta-intent). the cold +
would-arpad SUPERPOSITION is applied at the gate (PHASEGATE/VERIFY), per brain-review and P29.

**the check binds only if the worker was given examples.** "would arpad write this?" is an adjective,
and a worker resolves an adjective against its own priors ([[principle-40-idiom-needs-exemplars]]).
DOCTRINE runs BEFORE this state for exactly that reason: it resolves the purpose register
([[principle-41-rigor-scales-with-purpose]]) and the language row, loads the bound doctrine set
(`b-recall -b code <<'EOF'`, the task on the next line, then `EOF`), and writes the before/after pairs into the worker's prompt
along with the find-exhaustively ask. rust additionally has `aav-rust-implementer`, which carries the
same doctrine natively ([[principle-23-standing-decisions]]); every other language gets it because
DOCTRINE injected it, not because the worker happened to know it.

## when the gate fires (the budget, not the phase count)
PHASEGATE is bought by the SIZE of what the phase changed, never by finishing a phase. at each
phase boundary run:

```bash
b-gate phase -t SIZE   # SIZE: the plan's S, M or L for this phase; -l on the final phase
```

and emit what it prints: `gate N` -> `implemented`, PHASEGATE with N reviewers (2-6); `defer` ->
`phase_done`, the next phase; `defer` under `-l` -> `last_deferred`, straight to VERIFY. its word
is final. the score is code lines plus a weight per added, deleted or renamed file; PROSE scores
nothing (`shape.toml`'s `[scan] prose`), so a doc-only build never buys the cold review - it gets
STYLE. the tag is the plan's expected size and outranks a small diff, which is how a two-line change
to an authorization door still buys the gate.

**small phases accumulate, and the script remembers them.** it keeps the pending score per checkout
from the last gate that actually ran, so three deferred phases are reviewed together; `-l`
gates whatever is still pending. a ref git cannot resolve stops it with a usage error - never read
that as `defer`.

this exists because the gate used to cost the same whether the phase was 5885 new lines or two
lines of formatter appeasement, so a trivial fix bought a full multi-lens review and the review
budget went where the phases were, not where the risk was
([[principle-53-rigor-scales-with-the-change]]). a stale count in a doc is the canonical false
arm: re-measure it, correct it, move on ([[principle-54-a-count-is-a-measurement]]).

`b-shape` is the gate's STRUCTURE input - file lengths, folder fan-out,
duplicated datatypes - and that half runs at every gate, armed or not, because none of it is
visible in a diff (P27, P28).

## stops (the only sanctioned post-sanction pause)
a transition to a `blocked`/ASK state is the only legit stop: cross back and ask via brain-meta-intent.
never assume post-sanction, but do not pause needlessly - a decision he'd want = ask; a mechanical
detail = proceed. a gate below threshold routes BACK (to REMEDIATE), never forward.

## reporting
only at gates, and only what he cant see himself: verdicts, blockers, the single next action. no diff
recaps. lowercase, terse, ends on the next action.

## hard rules
never assume post-sanction. never fabricate. never commit/push/bump versions unless told. never trample
his manual edits. channel intensity into named constraints, never abuse sub-agents.
