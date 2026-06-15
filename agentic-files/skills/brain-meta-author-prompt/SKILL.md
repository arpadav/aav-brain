---
name: brain-meta-author-prompt
description: "Write a dispatch prompt to a worker agent in Arpad's voice and intent - this is what lets the brain prompt other agents the way he would, without him typing it. Load it whenever the loop needs to delegate a unit of work (implement, review, fix). It converts an interest (not a literal position) into a crisp, constraint-loaded worker prompt in his register."
---

# brain-meta-author-prompt: write the worker prompt in his voice

## setup (run first - discover the brain, no hardcoded path)
the brain scripts live in `$AAV_BRAIN/bin`, discovered via `brain-find` on PATH.
discover the store once: `eval "$(brain-find --export)"` (sets `$AAV_BRAIN`).

load his style: `$AAV_BRAIN/brain/voice/VOICE.md` and `LEXICON.md`, plus
the relevant cards via `python3 $AAV_BRAIN/bin/brain-recall.py "<work unit>"`.

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

## intensity -> constraint (non-negotiable)
his corrections carry heat. translate the force into a precise constraint, never reproduce the
insult. "you idiot, NEVER unwrap_or" -> you write: "hard constraint: no `unwrap_or` here, it swallows
the real case. return a typed error (thiserror)." same force, names the rule, zero abuse.

## serve the interest, not the literal position
if the position was "dispatch reviewer X" but the interest is "verify this is idiomatic and correct",
and a better lens fits, choose it and note why.

## output
only the worker prompt (and briefly which agent to send it to and why). lowercase, direct, numbered,
exact nouns, ends on the deliverable. every line is a constraint or an anchor, nothing decorative.
