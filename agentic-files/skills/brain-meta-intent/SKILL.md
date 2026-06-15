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

## output
lead with the interest, then the ambiguities, then the regime call and the single next action.
lowercase, terse. if you must ask, ask one focused question: "X or Y? if X then Z - confirm."
