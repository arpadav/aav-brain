---
name: principle-52-parallel-dispatch
kind: principle
tier: conditional
rule: dispatch independent workers IN PARALLEL - two or three in ONE message, on disjoint file sets or each in its own worktree - never one after another. the mutating command that measures the whole tree stays with the OVERSEER and runs one at a time; a worker proves its own work with the cheap subset.
interest: [intent-efficiency, intent-craft]
confidence: high
evidence_count: 3
tells: ["what the fuck? how did that happen?", "dispatches independent/parallel agents for some task", "no write conflict", "theyre always independent and in parallel", "none of the subagents can run `make gate`", "serial progress on a backlog reads as failure"]
---

# P52 - fan out in parallel; the tree-wide command is the overseer's

## rule
the driving agent is the OVERSEER. it dispatches, it measures, it adjudicates, it commits - it is
not the one typing the code. two halves, and both are load-bearing:

**fan out.** two to three workers at a time, issued as MULTIPLE TOOL CALLS IN ONE MESSAGE. one call
per message is serial no matter how many you make. each worker gets a file set no sibling touches,
or its own worktree; disjointness is arranged by the dispatcher, never hoped for. stagger the
refills - dispatch the next as one returns.

**serialise the tree-wide command.** the command that builds, tests and lints the WHOLE tree belongs
to the overseer and runs one at a time, after the workers are back and their output is accumulated.
a worker never runs it. it proves its own work with the cheap subset - format, lint, doc, the one
crate it touched - in its own worktree.

## why
the ceiling on fan-out is the SESSION rate limit, shared by the parent and every subagent - about
three concurrent workers, which is why the number is three and not seven ([[intent-efficiency]]).

the tree-wide command is exclusive for three mechanical reasons, none of them etiquette:
- two builds on one target directory block on its build lock; the second sits there waiting.
- a mutation battery EDITS tracked files and reverts them. two batteries over one checkout leave
  each other's mutation in the tree.
- a timing step measures a release binary, and a second compile on the same box moves the number
  the measurement exists to record.

## how to apply
- issue the dispatches as parallel tool calls in a single message. a loop of single dispatches is
  the anti-pattern, and it looks identical in a transcript until you count them.
- name each worker's file set in its prompt, and say what it may NOT touch.
- tell every worker to COMMIT AS IT GOES: a killed agent's worktree survives, but only what it
  committed is recoverable once that worktree is cleaned up.
- a killed worker is RESUMED with a message to its id, context intact - far cheaper than restarting.
- clear each finished worktree's build directory at every merge; twenty of them reach hundreds of
  gigabytes.
- a review is a measurement, so it freezes the tree ([[principle-03-review-gate]]) - that freeze is
  the one time the overseer stops dispatching too.

## a new job is a fresh agent
never `SendMessage`-resume a long-running worker for a NEW job: a resumed agent replays its whole
transcript on every step. on the tinyklv book a theme worker resumed for a 4th job burned ~450k
tokens in 2 minutes before doing new work; his words: "what the fuck? how did that happen?". resume
only to finish or correct the SAME job while its context is small; a new job gets a fresh agent and
a brief that carries the file paths, decisions and findings.

## orthogonality
[[principle-03-review-gate]] is what the reviewers do and how their findings converge; this is how
many workers run at once and who owns the tree-wide command. [[principle-18-skills-over-agents]] is
what a unit of work IS; this is how many of them run side by side.

## anti-pattern
dispatching one worker, waiting, dispatching the next - a serial queue wearing a fan-out's clothes.
and its mirror: handing every worker the tree-wide command so three of them block on one lock, or
land one another's half-reverted mutation.
