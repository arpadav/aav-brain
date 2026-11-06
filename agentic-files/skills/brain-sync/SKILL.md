---
name: brain-sync
description: "Push the edit copy's brain to GitHub main: its submodules (logs), the brain store with every learner worktree folded in, then the home repo that holds it. Load this when he says 'brain-sync', 'sync the brain', 'push the brain'. Each repo's work goes through a short-lived local branch that merges main in and fast-forwards main; an obvious conflict is resolved automatically, a contradicting or intent-dependent one stops and is put to him. Once every repo is pushed, b-sync runs `sy`, which pulls the result into the install copy and switches it, so nothing is left pulled-but-not-live."
---

# brain-sync

Push every repo of the edit copy to `main`, innermost first: the brain's submodules (e.g. `logs`), the brain store, then the home repo that holds the brain. `b-sync` acts on the edit copy whichever copy it runs from. The brain store's sync merges in every learner worktree (a `learn/*` branch, brain-learner), removes it and deletes its branch. The identity and message of every commit the sync makes are the script's, and `b-sync -h` names them.

## run

```bash
b-sync -c   # optional: what each repo holds, and its learner worktrees
b-sync
```

Exit 0 means every repo is on `origin/main` with the `brain-sync` branch gone, and `sy` brought it into the install copy and switched it: `b-sync` is the apply step. The steps each repo goes through, and every stop with its exit code, are `b-sync -h`. Relay every `b-sync: warning:` line to him.

## verify (always, after exit 0)

Read the install copy, `~/.config/aav/home`: `git -C ~/.config/aav/home status -sb` is clean on `main...origin/main`, at the commit the edit copy's home `main` is; `readlink -e` resolves every `~/.claude/skills/brain-*` link and `~/.claude/agents/brain` (none broken); `b-find` prints `~/.config/aav/home/brain`; `b-walk -h` runs. In every repo `b-sync -c` lists, `git status -sb` is clean on `main...origin/main`. A broken link or a stale install copy is not reported as "not applied": read the error, fix it, and rerun; if the fix is a decision that is his, stop and ask him interactively. Never finish with "pending", "not applied yet" or "you need to run X" - the run ends either fully applied and verified, or in a question to him.

## on a conflict (exit 3)

`b-sync` names the repo and its unmerged files and leaves the merge in progress on the `brain-sync` branch - a merge of origin, of local `main`, or of a learner's `learn/*` branch alike. Resolve each file, `git -C <repo> add` it, then run `b-sync` again; it resumes (`b-sync -h`) and continues outward.

A conflict is obvious, and resolved without asking, when one of these holds:

- The file is generated from a tracked source: take either side, then rebuild it from that source (e.g. `docs/DEV_FLOWCHART.md` -> `b-flow`). Merge the source, never the output.
- The file is append-only data (e.g. `*.jsonl` in `logs/`): keep both sides' lines, dropping exact duplicates, in timestamp order.
- The submodule pointer conflicts in the outer repo: take the commit the inner repo was just pushed at.
- The two sides changed different, non-overlapping lines and git only refused on proximity.
- Both sides made the same change, or one side's change plainly contains the other's.

Anything else - both sides changed the same lines of a principle, a skill, a script or a config in ways that contradict, or combining them would mean guessing what he meant - STOP and ask him interactively before touching it: show the repo, the file and both hunks in plain words, and ask which to keep or how to combine them. Never pick a side silently, and never force-push.

## on any other stop (exit 5)

The message names the repo and the stop (`b-sync -h` lists them), and a scan stop prints what it found. Report to him what was found; never reset, never force, and never rewrite or drop the commits a scan named - what becomes of them is his call.

- `learner`: a learner worktree holds uncommitted work, and its learner may still be running in another project. Name the worktree to him; never commit, stash or discard it yourself.
- `apply`: every repo is already pushed; only `sy` is missing or failed. Read its error, fix the cause, and run `sy`; a cause that is his decision is put to him.

## rules

- Only `origin`'s `main` is pushed; the `brain-sync` branch is the one local branch the sync makes, and it is deleted once `main` follows what origin accepted. Never `--force`.
- `b-sync` always runs `sy` itself; it never hands that step back to him.
- The run ends fully pushed, merged and applied, or stopped and reported to him: a conflict (exit 3) with a question, any other stop (exit 5), a wrong command line (exit 2), or a crash or no edit copy (exit 1, "run /home-setup"). Never a status report of work left undone.
