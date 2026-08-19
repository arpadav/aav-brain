---
name: brain-meta-drive
description: "The shared flow-traversal engine. INVOKED ONLY BY THE FOUR ENTRY SKILLS - brain-plan, brain-execute, brain-review, brain-self-refine - which MUST call Skill(brain-meta-drive) as their last step; it is never typed by the user and never invoked directly by a request. It walks flow.json from the entry's $STATE to a terminal by executing brain-walk.py, dispatching each state's owner (a brain-meta-* skill or a cold agent), recalling per state, and looping the threshold gates. It does NOT reconstruct state - the entry does that."
---

# brain-meta-drive: the shared flow-traversal engine

every entry skill is thin and ends the same way: *reconstruct my region's state -> set `$STATE` (entry
node) + `$REGIME` -> load this engine.* brain-meta-drive owns ONLY the walk: it steps `flow.json` from
`$STATE` to a terminal, running each state's owner. it is the ONE trampoline (P31) - the four entries
never reimplement it.

## what calls this (and what they hand you)
the caller (`brain-plan` @RECON, `brain-execute` @IMPL, `brain-review` @REVIEW, `brain-self-refine`
@SR_SCAN) has ALREADY:
- reconstructed its region's state (execute: the plan in plans/ + git; self-refine: selection-state in
  the transcript + decisions.jsonl). **the engine reconstructs nothing.**
- set `$STATE` = its entry node, `$REGIME` = ask-first | execute-through (read it from the entry, do
  NOT infer it from "did we cross SANCTION" - review and self-refine reach DONE without crossing it),
  and `$MODE` = `--self-refine` for the refine entry, EMPTY for every other.

**forward `$MODE` verbatim on every walk call; never infer it.** a guarded transition resolves by
mode, so the same (state, event) leads somewhere different in a refine run - `VERIFY --more_phases-->
DOCTRINE` exists only when the flag is absent. dropping it silently takes the build branch.

## setup (run first - discover the brain, no hardcoded path)
the brain scripts live in `$AAV_BRAIN/bin`, discovered via `brain-find` on PATH, so they
run the same on any machine:
```bash
eval "$(brain-find --export)"   # sets $AAV_BRAIN
```

## EXECUTE, do not read-and-reason (the cardinal rule)
the flow is a program; you RUN it, you do not interpret it. you MUST execute `$AAV_BRAIN/bin/brain-walk.py` for
every step and treat its stdout as AUTHORITATIVE. do NOT open `flow.json`/`flow.toml` and reason about
transitions yourself - that re-derives the machine by hand, non-deterministically, and is the exact bug
this design exists to prevent. if a script errors, FIX the error; never fall back to reading the data
file and guessing. same for brain-recall: run it, use its output; do not hand-walk graph.json.

## the trampoline (the engine itself) - loop from `$STATE` until a terminal
```bash
step=$(python3 $AAV_BRAIN/bin/brain-walk.py --state "$STATE")     # the state's owner + recall flag
```
- if the step's `recall: true` -> run `python3 $AAV_BRAIN/bin/brain-recall.py "<active task>"` FIRST to load
  the relevant cards. this is the ONLY call into the graph (context); the graph never decides the next
  step.
- **LOAD THE OWNER. this is the step that gets skipped.** `brain-walk.py` prints the literal call
  under every state that has one:
  ```
  LOAD ITS OWNER FIRST:  Skill(brain-meta-style)
  ```
  make that call. **you may not do a state's work until its owner is in context** - the same bar the
  walk output itself is held to. "run the owner" does NOT mean "do the state's work yourself": the
  owner skill IS how that state is done, and hand-rolling it inline discards the encoded method while
  looking, in the transcript, like the state ran.
  this is measured, not theoretical: `brain-meta-style` was named as owner 49 times and loaded twice
  (4%), `brain-meta-author-prompt` 19 times and loaded once (5%). the ONE owner that carries a literal
  call in its handoff - this engine - loads every time. a name is not an instruction.
  the two cold AGENTS (`brain-verifier` / `brain-review-gate`) are DISPATCHED instead, and the walk
  says so. a state owned by the entry itself, or by `brain-recall` (a script), prints no directive -
  those are the only states you act on directly.
- the owner returns an OUTCOME EVENT (`threshold_met` / `below_threshold` / `unsound` / `set_grew` /
  `drafted`, ...).
- get the next state from the data, never from your own judgement:
```bash
python3 $AAV_BRAIN/bin/brain-walk.py --state "$STATE" --on "$EVENT"
```

## cyclic refinement is REQUIRED (P03) - the gate loops never advance dirty
the flow encodes threshold loops; you do not advance a phase until its metric holds:
- **RECON..REORG**: per-file scrutiny + bidirectional reorg (P29, P27); the EXPAND back-edge grows the
  relevant-file set to a fixpoint as moves/reshapes implicate new peripherals.
- **PLAN -> PLANPROBE -> PLANGATE**: trace the plan through its worked example; `gap_found` /
  `below_threshold` loop to PLAN, only `threshold_met` crosses SANCTION. (PLANGATE rule lives in its
  flow-state doc - brain-meta-style:plan + the project reviewer when present.)
- **IMPL -> PHASEGATE -> VERIFY**: PHASEGATE `below_threshold` -> REMEDIATE -> PHASEGATE until the review
  converges; VERIFY `unsound` -> REMEDIATE until the build/test/bench is sound. only then advance.
- a gate below threshold routes BACK (to PLAN or REMEDIATE), never forward.

## boundary + stops
- **SANCTION** (only on entries that pass through it) is the regime flip ask-first -> execute-through;
  LOG the plan's decided-against forks to the trace (`brain-trace.py`) per the SANCTION state doc before
  flipping. for entries that never cross it (review, self-refine) the regime stays whatever the entry set.
- a transition to a `blocked`/ASK state is the only sanctioned pause: cross back and ask via
  `brain-meta-intent`. post-sanction, never assume - decision he'd want = ask; mechanical detail = proceed.

## the two cold agents vs the loaded meta-skills
`brain-verifier` and `brain-review-gate` are AGENTS on purpose: their value is a fresh, cleared-context
dispatch that never saw the author's framing (P03, P04). everything else (`brain-meta-author-prompt`,
`-style`, `-commit`, `-curate`, `-intent`, `-recall`) is a SKILL you LOAD into this loop. that is the
bag-of-skills composition (P18).

## reporting
only at gates, and only what he cant see himself: verdicts, blockers, the single next action. no diff
recaps. lowercase, terse, ends on the next action.

## the review barrier - a review's input tree is FROZEN
a review is a measurement, and a measurement of a moving target is noise. two rules, both hard:

1. **while ANY review agent is live, dispatch nothing that mutates the tree** - no worker, no edit, no
   `Write`/`Edit` by you. not "mostly nothing": nothing. a writer dispatched 29s after a background
   `brain-review-gate` once made it report a red suite that was green, and it then attributed the
   breakage to the diff under review. every finding downstream of that was suspect.
2. **N reviewers dispatched => BARRIER.** ALL N must return before ADJUDICATE or REMEDIATE begins. a
   partial set is NOT a converged set: fixing on `[1, N-1]` mutates the tree reviewer N is still
   reading, and its findings arrive describing a file that no longer exists. wait, converge, adjudicate,
   THEN fix.

the same exclusion covers writers: **no two mutating agents on an overlapping file set**. serialise
them, or give each `isolation: "worktree"`. two implementers on one crate 33s apart once forced the
second to verify itself against a hand-built mirror, because the crate did not compile mid-flight.

if this costs wall-clock, it costs wall-clock. a fast wrong answer is what this engine exists to
prevent (P04).

## findings are evidence, not verdicts (the ADJUDICATE state)
`PHASEGATE --below_threshold-->` lands on **ADJUDICATE**, never straight on REMEDIATE. classify every
finding against the artifact's stated contract before any of it becomes work:

| verdict | meaning | action |
|---|---|---|
| valid | a real defect | -> REMEDIATE |
| invalid | the finding contradicts the artifact's contract | REJECT + log the reason |
| deferred | real, but a later phase delivers it | REJECT for this phase + log |

the two classes that MUST be rejected, because "fixing" them cannot terminate:
- **deliberate incompleteness.** a tutorial whose deliverable IS `todo!()`, a lab that ships red on
  purpose, a scaffold carrying `[NEEDS INPUT]` markers. "this is unimplemented" is a DESCRIPTION of a
  working artifact, not a finding. fixing it destroys the thing.
- **out-of-phase work.** a multiphase plan is phased on purpose; a reviewer asking phase N to contain
  phase N+1's deliverable is asking you to abandon the phasing.

log every rejection so the next pass inherits it instead of re-litigating:
`brain-trace.py --skill <entry> --decision "<finding>" --chosen "rejected" --reject "<finding>=<why>"`.
a reviewer that self-reports uncertainty, or that you catch fabricating, is discounted wholesale -
verify its claims yourself before any of them become work (P04, P08).

## hard rules
never assume post-sanction (decision he'd want = ask; mechanical detail = proceed). never fabricate.
never commit/push/bump versions unless told. never trample his manual edits. channel intensity into
named constraints, never abuse sub-agents. FREEZE the tree under a live review and BARRIER on all N.
adjudicate before you remediate.
