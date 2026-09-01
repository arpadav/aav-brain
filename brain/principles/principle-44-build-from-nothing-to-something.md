---
name: principle-44-build-from-nothing-to-something
kind: principle
rule: he learns by building a foundation from nothing to something, one atomic step at a time, each step touching the last one's output - never by memorizing a finished artifact. any explanation or teaching material is a ladder he climbs interactively, not a reference he is handed.
interest: [intent-comprehension, intent-efficiency]
confidence: very-high
evidence_count: 26
tells: ["its not memorization that works - its building up foundation from nothing -> something, interactive", "do you not understand how to start simple and BUILD ONTOP of existing knowledge?", "the NEXT one should BUILD ONTOP of it, by showing my first kernel from previous lab, and ADDING to it, so i can see the DIFFERENCE", "i want it interactive like I WRITE THE KERNEL in some of them not just run commands", "even the first lab just takes 30 minutes to LEARN what is actually happening before i can actually do anything", "do NOT make me edit fucking markdown tables, the formatting/input is so dogshit - this is NOT a lab its manual grunt work and i am learning nothing", "dont do that again. just make them all .cu files that i have to edit. dont make me move them individually"]
---

# P44 - build from nothing to something

## rule
he does not learn by reading a finished thing. he learns by **building one**, in atomic steps, where
**each step's starting point is the previous step's finished output** - so the change between them is
small, visible, and his.

teaching material that violates this is worthless to him no matter how correct it is. a 400-line
file handed over with "run these commands" is a reference, not a lesson: he spends thirty minutes
reverse-engineering it before he can do anything, and what he ends up with is recognition, not
recall.

## why
memorization does not survive contact with an interview or a debugger. a number he *produced* does
([[intent-comprehension]] - he will not outsource his mental model). "padding removes bank conflicts"
is a sentence he forgets; "i removed 65 million conflicts and the runtime moved 2%" is a thing he
knows, because he watched it happen to code he wrote.

the cumulative constraint is what makes a profiler useful at all: if step N+1 starts from step N's
kernel, the tool shows a **delta against something he already understands**. if it starts from new
boilerplate, the tool shows a wall of numbers about a stranger's code, and the lesson is lost in the
reading.

this is the pedagogy behind [[principle-40-idiom-needs-exemplars]] (an adjective teaches nothing; a
before/after pair teaches) and the reason [[principle-42-plain-english-questions]] insists a question
be built up from nothing rather than from the brain's vocabulary.

## how to apply
- **one idea per unit**, stated *before* any code. if it needs two ideas, it is two units.
- **each unit starts from the last one's finished artifact.** never re-introduce fresh boilerplate
  mid-ladder.
- **he writes the part that teaches.** given code is fully commented and exists only to hold the
  thing he writes; the blank he fills is the lesson.
- **make it interactive and self-checking** - it re-runs on save, it tells him pass or fail, it moves
  him on. never make him hand-edit a progress table or transcribe results; the program prints the
  number and the check asserts it.
- **ship units already in their final, edit-ready form.** a `.scaffold` file he must rename or move
  before he can touch it is busywork wearing a lesson's clothes - hand him the `.cu` file itself,
  already sitting where he opens it.
- **give the answers**, folded. a question with no answer is a dead end, not a test.
- end the ladder somewhere he builds the whole thing from a blank file.
- verify the check fails against the unfinished state - a test that passes on empty work is worse
  than no test.

## anti-pattern
a wall of pre-written code with "run these commands and record what you see"; units that each start
fresh so nothing accumulates; progress tracked by editing markdown tables; questions posed with the
answers withheld; "read this chapter, then do the exercise" ordering, when the measurement is what
makes the chapter mean anything.
