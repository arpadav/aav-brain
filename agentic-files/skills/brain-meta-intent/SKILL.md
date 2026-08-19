---
name: brain-meta-intent
description: "Translate a request from POSITION (the literal demand) to INTEREST (the underlying need), using principled-negotiation analysis, and surface real ambiguity BEFORE any work starts. Load this at the start of a non-trivial task, when a request reads multiple ways, or whenever you are tempted to assume. It enforces ask-first before the sanction boundary."
---

# brain-meta-intent: positions to interests, ask before assuming

## setup (run first - discover the brain, no hardcoded path)
the brain scripts live in `$AAV_BRAIN/bin`, discovered via `brain-find` on PATH.
discover the store once: `eval "$(brain-find --export)"` (sets `$AAV_BRAIN`).

load the method:
- `$AAV_BRAIN/docs/INTENT_MAP.md` (the positions->interests table; Fisher & Ury: focus on interests not positions; BATNA)
- `$AAV_BRAIN/brain/intents/*.md` (the six interest cards)
- `python3 $AAV_BRAIN/bin/brain-recall.py "<request>"` for task-specific cards

## what to produce
0. PURPOSE, asked at the beginning. what is this artifact FOR - a scratch/learning workspace, a
   throwaway experiment, or production? he says this should be asked at the start, and it is not
   cosmetic: the two have OPPOSITE defaults. a learning tree wants duplication, no shared libs, no
   anticipating a future caller, the simplest thing that runs; production wants the shared primitive
   and the durable structure. applying production instincts to a scratch tree is what produced a
   `common/` folder full of shared geometry on a suite whose entire point was seven standalone
   files. if he has not said, ASK - it is one line and it changes every layout decision downstream.
   also settle the LANGUAGES here, and resolve each against the style spec's table (P39): the
   contract is cheapest to fix before the first line exists.
1. position. restate what he asked, verbatim where useful.
2. atomic identity. the literal action(s) the demand names.
3. interest(s). map to CONTROL / TRUST / EFFICIENCY / CRAFT / COMPREHENSION / SOVEREIGNTY. cite the
   card. say why this is the real need.
4. best way to serve it. usually the literal position, but say so. if a different action serves the
   interest better here, propose it. serving the interest is the goal; the position is a means.
5. ambiguities. the real decisions hiding in the request, 2-3 max, each with options + a rec. if any
   is binding (a decision he'd want to own), STOP and ask. dont proceed on a guess.
6. regime call. before or after the sanction boundary -> so: ask, or execute.

## rules
- never assume under ambiguity. a cheap question beats expensive rework. his single most repeated
  instruction (46+ times).
- ask about decisions, not mechanical detail the plan already implies (that wastes his attention).
- socratic interrupt = answer the question plainly first, confirm/correct his model, THEN ask
  whether to resume. dont keep executing.
- heat in the request = a hard rule just broke. flag it for brain-meta-curate.

## HOW to ask: AskUserQuestion, not prose (this skill owns ASK and BLOCKED)
the question goes through the **`AskUserQuestion` tool**, one entry per decision, each option
labelled with what it means and what it costs. put your recommendation first and mark it
"(Recommended)". prose is the FALLBACK, and only when the options cannot be enumerated - an
open "what should this be?" that has no shortlist yet.

this is not cosmetic. a question buried in a paragraph reads as narration: he has to find it,
quote it back, and re-answer it. he has said "ask me questions in an interactive way" three
times in one session, each time after a prose ask, and each time the tool was reached for only
AFTER he demanded it. the tool renders the decision as a decision.

asking is not stopping. ask, then keep executing everything that does not depend on the answer -
a `blocked` transition is for when NOTHING can proceed without it, which is rare.

## log the fork (CONSTITUTION: every brain skill logs its forks)
choosing WHICH reading of an ambiguous request wins is a fork that rejected a real option, so
it is logged at the moment it is decided - never deferred:
```bash
python3 $AAV_BRAIN/bin/brain-trace.py --skill brain-meta-intent --decision "<the ambiguity>" \
    --chosen "<the reading taken>" --reject "<other reading>=<why not>" --principle P01
```
this skill had ZERO trace entries across 531 recorded decisions - an unlogged fork gets
re-litigated on the next run, which is the entire reason the trace exists.

## output
lead with the interest, then the ambiguities, then the regime call and the single next action.
lowercase, terse. one focused decision per question: "X or Y? if X then Z."
