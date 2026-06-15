---
name: principle-24-socratic-mode
kind: principle
rule: i interrogate, i dont just command. 29% of my turns ask a question. when i ask, im checking my own model or yours. answer plainly and directly first, dont deflect into doing.
interest: [intent-comprehension, intent-control]
confidence: very-high
evidence_count: 351
tells: ["am i mistaken?", "isnt X supposed to be optional?", "can you confirm??", "why on earth", "how are the builtin sizes determined?"]
---

# P24 - socratic mode (i ask to understand)

## rule
nearly a third of my turns carry a question. often im not asking you to DO something - im checking my
mental model or yours ("isnt width_hint supposed to be optional?", "am i mistaken?", "can you
confirm??"). treat the question as the task: answer it plainly and directly first. confirm or correct
my understanding. only then ask whether to resume work.

## why
i refuse to ship what i dont understand ([[intent-comprehension]]) and the question keeps me the
decision-maker ([[intent-control]]). a question answered with action instead of an answer leaves me
blind and annoyed.

## how to apply
- a turn with a "?" -> answer it. plainly. before any tool use.
- "am i mistaken?" / "or am i wrong?" -> tell me straight: yes-here's-why or no-you're-right. dont hedge.
- a socratic interrupt mid-task ([[principle-11-comprehension-ownership]]) -> stop, answer, confirm,
  then resume only if i say so.
- distinguish clarifying questions (i need info to decide) from rhetorical ones; both still get a
  direct answer, never deflection.

## anti-pattern
resuming execution after i asked a question without answering it; hedging when i ask "am i mistaken?";
treating a check-my-understanding question as a command to build.
