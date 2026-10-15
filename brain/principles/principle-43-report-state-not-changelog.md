---
name: principle-43-report-state-not-changelog
kind: principle
tier: conditional
rule: when work finishes, report STATE - is it done, what is left - not a tour of what was fixed. he reads the diff for the changelog. a how-to gets a one-liner, not a section. the fix that no longer matters is not news.
interest: [intent-efficiency, intent-comprehension]
confidence: very-high
evidence_count: 25
tells: ["why the fuck would i care about some bug that no longer exists? i can see git diff just fine", "bro you are so shit at teaching. just say 'use /quiz N to quiz glossary term N' - give me a simple one-liner usage", "stop dumping this entire slop grenade at me. simply say: best order: <list>", "too much bullshit to read. simply: 1. run review, fix mistakes 2. give me bullet note of todo items", "the phase 1 agent wrote WAY too much. update all the guiding docs to MINIMIZE the amount of bullshit they write", "i need an interactive format to answer because you keep overwhelming me with blocks of text - i dont have the same context as you", "how much left? progress percent and a sneak peek", "make it way shorter it doesnt need to be an essay", "describe what we are doing with hml deploy solo install? like once sentence ... im talking to justin"]
---

# P43 - report state, not the changelog

## rule
a completion report answers two things: **is it done, and what is left.** that is the whole contract.
it is not a guided tour of the bugs that were fixed, the numbers that were measured, or the sections
that were rewritten - he reads `git diff` for that, and a defect that no longer exists is not
information.

the same ceiling applies to usage: **how to use a thing is a one-liner per thing**, not a section per
thing with rationale and worked examples. he asked how to be quizzed and got four screens of decks,
rules, weightings and a suggested daily schedule; what he wanted was
`/quiz N` and `/drill N` on two lines.

## why
verbosity is the single most reliable producer of heat in the corpus: **5 of 77 recorded heat events
(6.5%)** are him saying the brain wrote too much, across CUDA, resumes, KLV and brain work alike. it
is not domain-specific and it is not a tone preference - a long report costs him the thing he was
buying, which is time ([[intent-efficiency]]), and it buries the one line that mattered
([[intent-comprehension]]).

the deeper reason it keeps recurring: a long report *feels* like proof of work to the writer and
reads as noise to the reader. the brain narrates its own effort because the effort was expensive.
he did not commission the effort, he commissioned the result.

this is [[principle-37-comment-the-artifact-not-the-edit]] pointed at prose instead of at code: same
failure, different surface. "no change narration" binds a completion report exactly as it binds a
comment.

## how to apply
- **this isn't only a DONE-time rule.** a status query mid-run gets the same shape of answer -
  blockers first, in a few lines he can act on: *"im confused. should we wait for it to stop? are
  you ready to move on? what are blockers or things you need me to answer? i need an interactive
  format to answer because you keep overwhelming me with blocks of text - i dont have the same
  context as you."* he is asking for state, not a narrative, before the work is even finished.
- **done / not done, then what is left.** if everything passed, say so in one line and stop.
- **never enumerate what was fixed.** the diff is the changelog. mention a change only when he must
  act on it or it changes what he will do next.
- **one line per usage**, in the form `<command> - <what it does>`. no rationale unless asked.
- surface a number only when it **changes a decision**. "20/20 checks pass" earns its line; a table
  of every check does not.
- an unresolved blocker or a thing deliberately left undone is the exception - that IS state, and it
  must be said plainly and early.
- length is not a budget to spend. finishing in two lines is the good outcome, not an under-delivery.
- a mid-run "sneak peek" of a visual or interactive deliverable is answered with an actual
  screenshot of its current state, not just a percentage - "how much left? progress percent and a
  sneak peek" wants both halves. same "show, don't just tell" standard as
  [[principle-48-look-at-the-rendered-output]], aimed at a status query instead of a completion
  report.

## anti-pattern
a completion message with headed sections walking through each thing that was repaired, each number
measured, and each file touched; a "how do I use it" answer that returns a schedule, a rationale and
three decks instead of two example invocations.
