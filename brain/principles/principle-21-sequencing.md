---
name: principle-21-sequencing
kind: principle
rule: i think and instruct in ordered steps. honor the sequence: first X, then Y, lastly Z. do the steps in the order i gave, and run sanctioned steps back to back.
interest: [intent-control, intent-efficiency]
confidence: very-high
evidence_count: 436
tells: ["first", "then", "next", "after that", "once you", "lastly", "1. ... 2. ... 3."]
---

# P21 - sequencing is how i work

## rule
my single most prevalent tell (436 turns / ~36%). i decompose work into an ordered sequence -
numbered lists and "first / then / next / once you / lastly". the order is the instruction. execute
the steps in that order, dont reorder them, dont skip ahead, and once a sequence is sanctioned run
the steps back to back ([[principle-10-autonomy-after-sanction]]).

## why
sequencing is how i keep control of a multi-step task ([[intent-control]]) while still getting
leverage ([[intent-efficiency]]). a numbered list is a contract: each item is a checkpoint i can
verify. reordering breaks my mental model; pausing between sanctioned items wastes my attention.

## how to apply
- a numbered/ordered prompt -> do the items in that exact order. surface results per item if a gate
  needs it, otherwise flow to the next.
- "first X then Y" -> X must finish (and pass) before Y.
- "lastly / finally Z" -> Z is the closer, do it last, dont front-load it.
- when authoring worker prompts, mirror this: number the asks, order them, put the closer last.
- my common closer asks: run fmt, regen charts, re-run the style pass. these go at the end.

## anti-pattern
doing step 3 before step 1; collapsing my ordered list into one blob; pausing for approval between
two steps i already sequenced and sanctioned.
