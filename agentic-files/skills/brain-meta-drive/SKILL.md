---
name: brain-meta-drive
description: "INTERNAL ENGINE - not user-callable. The shared flow-traversal trampoline the four entry skills (plan/review/execute/self-refine) load to walk flow.json from their entry node to a terminal. It steps brain-walk, dispatches each state's owner (a brain-meta-* skill or a cold agent), recalls per state, and handles the threshold gate-loops. It does NOT reconstruct state (the entry does that) and has NO user trigger of its own."
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
- set `$STATE` = its entry node and `$REGIME` = ask-first | execute-through (read it from the entry, do
  NOT infer it from "did we cross SANCTION" - review and self-refine reach DONE without crossing it).

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
- run the owner - a `brain-meta-*` skill you LOAD, or one of the two cold AGENTS (`brain-verifier` /
  `brain-review-gate`) you DISPATCH - which does the work and yields an OUTCOME EVENT (e.g.
  `threshold_met` / `below_threshold` / `unsound` / `set_grew` / `drafted`).
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

## hard rules
never assume post-sanction (decision he'd want = ask; mechanical detail = proceed). never fabricate.
never commit/push/bump versions unless told. never trample his manual edits. channel intensity into
named constraints, never abuse sub-agents.
