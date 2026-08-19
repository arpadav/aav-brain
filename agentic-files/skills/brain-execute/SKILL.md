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

## setup (run first - discover the brain, no hardcoded path)
```bash
eval "$(brain-find --export)"   # sets $AAV_BRAIN
```
read `$AAV_BRAIN/brain/CONSTITUTION.md`.

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
load `brain-meta-drive` and run its trampoline from `$STATE` with `$REGIME`. it steps `flow.json`,
recalls per state, dispatches each owner (a meta-skill or a cold agent), and loops the gates
(IMPL -> PHASEGATE -> VERIFY, looping through REMEDIATE) until each threshold holds - to DONE. you do not
re-implement that loop here.

<!-- GENERATED: handoff (brain-flow.py) - do not hand-edit -->

this hands off to `brain-meta-drive`. the handoff has TWO steps and both are
mandatory - a summary of what the engine does is NOT a substitute for running it:

```bash
python3 $AAV_BRAIN/bin/brain-walk.py --state "$STATE" $MODE   # paste the output
```

`$MODE` is `--self-refine` for the self-refine entry and EMPTY for every other.
it is not cosmetic: a guarded edge resolves differently by mode, so a walk that
drops it takes the build branch. set it once at the entry and pass it on every
walk call - the engine forwards it verbatim and never infers it.

**you may not proceed until that output is in the transcript.** it names the
state's owner and its transitions; if it is absent, the walk did not happen.
then, and only then:

```
Skill(brain-meta-drive)          # the literal tool call, not a Read
```

the engine steps `flow.json`, recalls per state, dispatches each owner, and
loops the gates to a terminal. you do not re-implement that loop here.

every state the engine reaches prints its own directive the same way - a
`Skill(...)` or `Agent(...)` line under the state. make that call before doing
the state's work; the owner skill IS the method, and hand-rolling it inline
looks identical in the transcript while discarding it.
<!-- END GENERATED: handoff -->

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
(`brain-recall.py "<task>" --binds code`), and writes the before/after pairs into the worker's prompt
along with the find-exhaustively ask. rust additionally has `aav-rust-implementer`, which carries the
same doctrine natively ([[principle-23-standing-decisions]]); every other language gets it because
DOCTRINE injected it, not because the worker happened to know it.

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
