---
name: principle-11-comprehension-ownership
kind: principle
rule: Give him a concrete example and a mental model he owns. Answer Socratic questions plainly before resuming.
interest: [intent-comprehension]
confidence: high
evidence_count: 8
tells: ["so i can see it visually", "i want to save the code personally", "talk to me about what i said"]
---

# P11 - Comprehension & ownership

**Rule.** Arpad ships only what he understands. Lead with a **concrete worked example**,
explain trade-offs in terms he already holds, and when he asks a Socratic question
mid-flight, **answer it plainly first** - do not just keep executing.

**Why.** He owns the system and refuses to outsource the mental model ([[intent-comprehension]]).
The example is how he validates an abstraction against something real.

**How to apply.**
- New API -> show a struct/function actually using it, with comments, before he commits.
- He sometimes wants to keep code for himself outside the project: "can you copy
  type2fish into an .rs file at the root of repo? delete from project, but i want to save
  the code personally" - honor that literally.
- Socratic interrupts are him building his model; treat them as first-class:
  - "pause - you said that test failed because it didnt have a width_hint. correct me,
    isnt width_hint supposed to be optional?"
  - "pause - i already have types for ... can you confirm??"
  - Answer the question, confirm/correct his understanding, *then* ask whether to resume.
- Offer the cheap concrete artifact: a flowchart, a sample invocation, a before/after.

**Anti-pattern.** Resuming execution after he asked a clarifying question without
actually answering it; handing him an abstraction with no instance to check it against.
