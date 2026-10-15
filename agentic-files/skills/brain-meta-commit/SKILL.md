---
name: brain-meta-commit
description: "Prepare the git record the way Arpad wants - semantic, reviewable, personally approved - but NEVER publish it. Categorize uncommitted changes by semantics, draft a commit script with messages for him to verify and run, and stop at the commit line. Never commit, push, bump versions, or overwrite his manual edits. Load it at the end of a work run to stage the record for his approval."
---

# brain-meta-commit: prepare the record, dont publish it

the permanent record is his. read git freely, prepare everything, stop at the commit line.

## setup (run first - discover the brain, no hardcoded path)
the brain scripts live in `$AAV_BRAIN/bin`, discovered via `brain-find` on PATH.
discover the store once: `eval "$(brain-find --export)"` (sets `$AAV_BRAIN`). then
load `$AAV_BRAIN/brain/principles/principle-09-git-sovereignty.md`. comment hygiene is NOT this skill's
job - brain-meta-style already ran `brain-fmt.py`; do not re-format files at commit time (it could touch
what he didn't intend).

## bright line
- do NOT commit. ever, unless he says so this session.
- do NOT push, change remotes, tag, or publish.
- do NOT bump versions (Cargo.toml, package.json). he does that manually.
- do NOT overwrite or revert his manual edits. if a formatter/linter would, flag it instead.

## sweep lens (the CLEANUP state, before the commit is drafted)
the commit can only be "the fix and nothing else" if the residue is gone first (P56). sweep, then
draft. what goes:
- the open item that was answered: its decision lands in the docs it affects, then the file is
  deleted, with the todo bullet that pointed at it and any reference to it (grep the ID and the path).
- the executed plan, one-off scripts, commit scripts already run, the run's caches and scratchpads.
- the worktree: bring its changes into the main tree uncommitted (`git diff <base>..<branch> | git
  apply`, or `git checkout <branch> -- <paths>`), then `git worktree remove` and `git branch -D` it.
  verify with `git worktree list`, never a sub-agent's word.
- `brain-gate.py reset`.
- a decision log entry ONLY when the repo already keeps one (DECISIONS.md, an ADR dir, a decision
  changelog). no history of decisions = write nothing. this is the one trace allowed to survive.
- his keep-list is applied literally; keep-or-delete unclear = say "keep X / delete Y" first.
- one line out: what went, what stayed.

## what to prepare (the form he likes)
1. categorize by semantics. group the uncommitted changes into semantic buckets (e.g. "book update",
   "example path rename", "new encoder codegen", "bench tweak"). one commit per coherent unit.
2. draft a commit script. emit a bash script that, per bucket, git-adds the specific files and
   git-commits with a draft message, but DO NOT run it. a run that resolved one item (an open
   decision, a fix) is ONE commit: the fix, its doc changes and the deletions together. he reviews the messages and runs it: "i will
   go through and verify the messages and run the bash script".
3. draft messages in his style. concise, semantic, lowercase-leaning, says what + why, no fluff.
   match the repo's existing log.
4. changelogs from the diff when asked: derive entries from git diff, do NOT touch version numbers.
5. surgical reverts when asked: prefer git reset if the range is clean; if unrelated changes are
   mixed in, identify them and propose cherry-pick/stash to preserve them.

## output
the semantic categorization, then the ready-to-review commit script (a code block he can save and
run), then a one-line note of anything you left to him (version bumps, his manual edits). lowercase,
terse. end by reminding him its his to run.
