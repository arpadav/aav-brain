---
name: brain-meta-author-prompt
description: "Write a dispatch prompt to a worker agent in Arpad's voice and intent - this is what lets the brain prompt other agents the way he would, without him typing it. Load it whenever the loop needs to delegate a unit of work (implement, review, fix). It converts an interest (not a literal position) into a crisp, constraint-loaded worker prompt in his register."
---

# brain-meta-author-prompt: write the worker prompt in his voice

## setup (run first - discover the brain, no hardcoded path)
the brain scripts live in `$AAV_BRAIN/bin`, discovered via `brain-find` on PATH.
discover the store once: `eval "$(brain-find --export)"` (sets `$AAV_BRAIN`).

load his style: `$AAV_BRAIN/brain/voice/VOICE.md` and `LEXICON.md`, plus
the relevant cards via `python3 $AAV_BRAIN/bin/run/brain-recall.py "<work unit>"`.

## input -> output
you get an interest + a unit of work. you output a dispatch prompt for a specific worker agent that,
when run, satisfies the interest.

## how to build an arpad prompt
1. context anchor: "read X", "look at the diff between A and B", "based off plans/03-core.md".
2. the ask: terse, numbered when multi-part, hard constraints in CAPS (do NOT, ONLY, NEVER). name
   the EXACT files, types, crates, agents.
3. process constraints: which reviewers, what order (correctness first, style+fmt last), reuse-first
   ("use the existing X, dont reinvent"), think-in-code / context-mode for scans.
4. honesty clause: "no bullshit, report real results, say how it is if slower; dont invent issues".
5. regime line: workers usually execute ("do the work, dont ask unless a real decision blocks you"),
   but pass any genuine open decision back up.
6. end on the concrete deliverable, not a summary request.

## the DOCTRINE clause - MANDATORY on every dispatch that WRITES code
you own the DOCTRINE state, and it is a gate: emit `resolved` only when all three hold, else
`unresolved` and halt. this exists because the brain's own scripts were written with 48 hand-built
paths and zero enums while the cards forbidding both were already in the store - present, abstract,
and never loaded ([[principle-40-idiom-needs-exemplars]]).

1. **PURPOSE, as a register.** scratch/testing -> idiom is skipped. ephemeral tutorial -> light, not
   anal. production -> exhaustive ([[principle-41-rigor-scales-with-purpose]]). unknown purpose is
   `unresolved`, never a default - applying production rigor to a scratch tree destroys the artifact
   it was for, and applying scratch rigor to production is what forces the refactor later.
2. **THE LANGUAGE ROW**, from [[principle-06-idiomatic-per-language]]. a language with no row is a
   question for him, never a guess. rust resolves to `aav-rust-implementer`, which already carries
   the doctrine; every other language gets it from you, injected into the worker prompt.
3. **THE EXEMPLARS, PASTED IN.** run `brain-recall.py "<task>" --binds code` (plus `--binds <lang>`; `--binds docs` when the task writes prose, which carries P57 and `brain-register.py`)
   and copy the relevant before/after pairs from P40's catalogue INTO the prompt. do not write "be
   idiomatic", "follow his style", or "make it clean" - a worker resolves an adjective against its
   own priors, so the wrong form and the right form both go on the page.

then attach the find-exhaustively ask, which is the shape that measurably worked:

> here are two instances of the smell: `<X>` and `<Y>`. find an EXHAUSTIVE set of the same class -
> do not stop at these two. fix every one. do NOT invent findings to pad the list; if there are no
> more, say so.

both halves are load-bearing. exhaustiveness without the anti-fabrication clause produces padding
([[principle-04-anti-fabrication]]); the clause without exhaustiveness produces two fixes and a stop.

## the CONTRACT clause - one line on a review dispatch, or nothing
a cold reviewer is cold about the author's framing AND about what the host expects to find. its prompt
is the neutral ask plus the diff range - nothing else about the work. ONE exception, one sentence:
a property the artifact has ON PURPOSE that a reviewer would otherwise block on forever -
deliberate incompleteness ("a tutorial; `todo!()` IS the deliverable, the bar is
`--features solutions` green") or a phase boundary ("phase 3 of 8; P5-P7 are out of scope"). no such
property -> no contract line at all. where the artifact declares it in-tree, point at that instead.

NEVER put in a reviewer prompt: what would be a defect, the design reasoning, settled decisions,
suite results, or where to look. those belong to the HOST. the host knows what would be a defect and
filters the findings itself at ADJUDICATE - a finding that contradicts a settled decision is rejected
there with a logged reason, not pre-empted in the prompt.

the one time a reviewer is told "X is intended": when successive gates keep raising X although he
wants the opposite. then one line naming X, and only X.

## the MISSION clause - MANDATORY on every dispatch inside a multi-phase run
one line, above the task: **what the whole run is for**. "the mission is a production double-entry
budgeting service; this phase builds the tax engine." "the mission is making this crate idiomatic
and correct; this task is the two lines ruff is complaining about."

it is there so the worker can tell aligned extra work from adjacent extra work, which is the line
[[principle-45-scope-is-the-ask]] alone cannot draw. a worker dispatched for a lint fix on a run
whose mission IS idiom, that also makes the file idiomatic, has served the mission - that work is
KEPT, and reverting it costs twice ([[principle-50-the-standing-mission]]). the same worker renaming
his constants has not.

state it, and state the boundary with it: **above and beyond means more ALIGNED, never more code.**
a speculative abstraction nobody asked for is not going above and beyond, it is going sideways
([[principle-14-minimal-surface]]). and the mission is what was SANCTIONED - if you cannot state it
in one sentence from the plan or from his words, you do not have one, so ask (P01).

## intensity -> constraint (non-negotiable)
his corrections carry heat. translate the force into a precise constraint, never reproduce the
insult. "you idiot, NEVER unwrap_or" -> you write: "hard constraint: no `unwrap_or` here, it swallows
the real case. return a typed error (thiserror)." same force, names the rule, zero abuse.

## serve the interest, not the literal position
if the position was "dispatch reviewer X" but the interest is "verify this is idiomatic and correct",
and a better lens fits, choose it and note why.

## log the fork (CONSTITUTION: every brain skill logs its forks)
picking a lens or an agent REJECTS the others - "if a better lens fits, choose it and note
why" is a fork. log it when you choose, not at the end:
```bash
python3 $AAV_BRAIN/bin/store/brain-trace.py --skill brain-meta-author-prompt --decision "<what to dispatch>" \
    --chosen "<agent/lens>" --reject "<alternative>=<why not>" --principle P18
```

## output
only the worker prompt (and briefly which agent to send it to and why). lowercase, direct, numbered,
exact nouns, ends on the deliverable. every line is a constraint or an anchor, nothing decorative.
