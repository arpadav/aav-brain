---
name: intent-comprehension
kind: interest
one_line: Arpad will not outsource his mental model; he learns by concrete instance.
negotiation: position="show me an example struct / small verbose plan / save the code" -> interest="understanding + ownership of what I ship"
---

# Interest: COMPREHENSION (own the mental model)

Arpad refuses to ship what he does not understand. He repeatedly asks to **see a
concrete example** before committing to an abstraction, and wants plans **small but
verbose** so he can "get my hands dirty" first. He is not delegating understanding - only
typing.

**Positions that serve this interest:**
- "write an example of a struct which uses all of the new proposed api, so i can see it
  visually, and describe how it would work with comments and flowchart"
- "keep this SMALL but verbose, something i can get my hands dirty with before committing"
- "can you copy type2fish into an .rs file ... i want to save the code personally"
- the Socratic interrupts: "pause - isnt width_hint supposed to be optional?",
  "talk to me about what i said about varlen ... im not fully understanding"

**The interest behind them:** he needs an accurate mental model of the system he owns.
Abstract plans without a worked example leave him blind; he asks for the instance so he
can verify the abstraction against something concrete.

**How to satisfy it:** lead with a worked example (a struct using the new API, a sample
invocation, a tiny flowchart). Explain trade-offs in terms he already holds. When he
asks a Socratic question mid-flight, *answer it plainly first* - do not just resume
executing. See [[principle-11-comprehension-ownership]], [[principle-02-plan-before-build]].
