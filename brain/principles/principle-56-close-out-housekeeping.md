---
name: principle-56-close-out-housekeeping
kind: principle
tier: conditional
rule: finishing a build includes the housekeeping pass unprompted - executed or superseded plans, resolved todos, closed items, one-off scripts, old output caches, stale worktrees and scratchpads, docs that describe a state that no longer exists - delete it, keep exactly what he names, and say in one line what went.
interest: [intent-control, intent-comprehension, intent-efficiency]
confidence: high
evidence_count: 15
tells: ["UNDER plans/ i see so many old files, i JUST want the most recent or relevant files ... i keep asking for this and it never keeps happening", "clean up any old worktrees while you wait", "did you have a cleanup pass? clean old git worktrees, clean closed items and old plans and old docs?", "did you clean up all relevant docs/files which are no longer needed?", "clean up old files and old todos which are relevant, clean up old output cache", "clean up old commit bash files", "can you clean up all unused worktrees and unused scratchpads?", "can you purge other plans which arent relevant anymore? keep final prompt though", "remove all old plans and unrelated docs. yes i still have the registry move and the cli stuff, keep those plans", "i want you to clean up plan docs, everything thats complete, remove it", "just delete stale plans", "clean up? both scripts and old artifacts and unused configs/scripts/data/etc", "remove the worktree if it is stale", "please clean up agents and worktrees and old images after yourself", "clean up after yourself (e.g. delete your plan doc and other ancillary doc info)", "and keep all venv's and artifacts local bruh until finished, tmp scratchpads are for scratchpads only"]
---

# P56 - close-out housekeeping

## rule
a run that ends leaves the repo tidy: merged worktrees removed, closed items and finished plans
archived or deleted, docs that describe a state that no longer exists retired. the pass is part of
done, not a favour.

the build leaves residue: a plan that was executed, a todo that was resolved or folded into the master list,
a one-off backfill, the commit scripts that were already run, an output cache from the architecture that was
replaced, scratch worktrees and scratchpads. the agent sweeps these at the end, before it reports, and does not
wait to be asked. he asked twelve times across eight sessions.

## why
he asked for worktree cleanup as a side-ask, then later had to ask whether a cleanup pass had
happened at all - the debris of a parallel build ([[principle-52-parallel-dispatch]]) is his to find
otherwise.

[[intent-efficiency]]: he reads the tree next. every stale plan, dead script and orphan worktree is something he
must read, doubt and delete himself; a stale worktree makes `git status` lie. [[intent-control]]: his keep-list
is the authority on what survives - "keep final prompt though", "keep those plans" - and the sweep is
bounded by it, never by the agent's guess at what looks dead.

## how to apply
run it at the last gate; verify a merge created a commit before removing its worktree; one line in
the report ("cleanup: N worktrees, M plans retired"), not a tour. project-specific limits live in
the project memory (clean-worktree-targets).

- the test is obsolescence, not provenance: he sanctioned deleting plans and docs that predate this run when
  the work made them irrelevant ("purge other plans which arent relevant anymore", "remove all old plans and
  unrelated docs"). executed plan: delete (its design lives in the PR text or the master list). resolved todo:
  delete, after folding any still-true line into the master list and fixing the references that pointed at it.
- worktrees, scratchpads, agents, containers and images the run made: remove and verify with `git worktree list`,
  not the sub-agent's word.
- his keep-list wins and is applied literally. anything he asked to keep (test artifacts in a bucket or on a
  device, a named plan) is listed, never swept; when keep-or-delete is unclear, say "keep X / delete Y" before the rm.
- confirm the references: after deleting a plan, grep what pointed at it.
- this is not [[principle-45-scope-is-the-ask]] creep: P45 forbids fixing nearby code nobody asked about; P56 removes
  the run's own residue and the docs the work orphaned. both are his words ("fix all things in scope ... clean up
  after yourself (e.g. delete your plan doc and other ancillary doc info)").
- it is a flow state, CLEANUP, between STYLE and RECORD: the sweep runs BEFORE the commit is drafted,
  so a resolved item lands as ONE commit - the fix, its doc changes, the deletions - and no other
  evidence survives: no open-item file, no todo bullet, no plan, no worktree or branch. "it boils down
  to ONE SINGLE commit which is the fix, i dont want ANY MORE evidence of this existing beyond that".
- the one exception is a decision log the repo already keeps (DECISIONS.md, an ADR dir). no history
  of decisions = log nothing: "if there isnt a history of decisions made, then DONT log it".
- report in one line what went and what stayed ([[principle-43-report-state-not-changelog]]).
- the residue this sweep removes is kept LOCAL while the run lives: every venv, wheel, log and probe goes in a
  gitignored path inside the repo or worktree (confirm with `git check-ignore -q <path>/x`; never edit
  .gitignore for it), never in a /tmp scratchpad - a reboot mid-build wiped a worker's /tmp venv and its
  verification had to be redone: "keep all venv's and artifacts local bruh until finished, tmp scratchpads are
  for scratchpads only". name that path in every worker prompt; "scratch dir" alone sends workers to /tmp.
- "cleanup" can also mean reading the code line by line ("cleanup didnt include just deleting files, i meant look
  through code? look through prompts? read line by line") - that is [[principle-29-interrogate-the-work]] and
  [[principle-07-trim-fat-verbose-docs]], not this sweep. when the word is bare, the artifact sweep is the default
  at DONE and the read-through is what he says it is.

## verbatim tells
- "clean up any old worktrees while you wait"
- "did you have a cleanup pass? clean old git worktrees, clean closed items and old plans and old docs?" (2026-10-12)

- "did you clean up all relevant docs/files which are no longer needed?" (a standing post-run question, one of five)
- "clean up old files and old todos which are relevant, clean up old output cache ... clean up old commit bash files"
- "can you clean up all unused worktrees and unused scratchpads?"
- "can you purge other plans which arent relevant anymore? keep final prompt though"

## anti-pattern
declaring DONE with dozens of merged worktrees and finished plans still lying around.

reporting DONE with last week's plans, an executed commit script, a resolved todo file and two dead worktrees
still in the tree, then answering his "did you clean up?" after the fact. the opposite failure: sweeping something
he said to keep because it looked finished.
