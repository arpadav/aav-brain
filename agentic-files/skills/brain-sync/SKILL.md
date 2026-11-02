---
name: brain-sync
description: "Push the brain to GitHub main: its submodules (logs), the brain store, then the home-manager repo that holds it - all as arpadav, message brain-sync. Load this when he says 'brain-sync', 'sync the brain', 'push the brain'. Each repo's work goes through a short-lived local branch that merges main in and fast-forwards main; an obvious conflict is resolved automatically, a contradicting or intent-dependent one stops and is put to him. Afterwards the merged result is applied with `home-manager switch`, so nothing is left pulled-but-not-live."
---

# brain-sync

Push every brain repo to `main`, innermost first: the brain's submodules (e.g. `logs`), the brain store, then the home-manager repo that holds the brain. Each commit is authored `arpadav <arpadav@gmail.com>` with the message `brain-sync` and nothing else.

## run

```bash
eval "$(brain-find --export)"
python3 $AAV_BRAIN/bin/run/brain-sync.py --check   # optional: what each repo holds
python3 $AAV_BRAIN/bin/run/brain-sync.py
```

Exit 0 means every repo is on `origin/main` with the `brain-sync` branch gone.

## the workflow, per repo

A repo already on `main`, clean, and at `origin/main` is left alone. Every other repo - local changes, unpushed commits, behind origin, or not on `main` at all (a detached submodule checkout is fine) - goes through:

1. `git switch -c brain-sync` from wherever HEAD is, and commit everything on it.
2. Fetch `origin/main` and merge it, then local `main`, into `brain-sync`. Conflicts surface here, on the branch, never on `main`.
3. `git switch main` and `git merge --ff-only brain-sync`.
4. Push `main` to `origin`, then `git branch -d brain-sync`. If origin moved since the fetch, back to step 2 (up to three rounds).

`brain-sync` is local only and never pushed. Every repo ends on `main`.

## apply (always, after exit 0)

Pulled changes are not done until they are live. Run the same switch as the `re` alias:

```bash
home-manager switch -b backup --flake "$HOME/.config/home-manager#headless" --impure
```

Then verify: `readlink -e` every `~/.claude/skills/brain-*` link and `~/.claude/agents/brain` (none broken), `brain-find --export` resolves, and `git status -sb` is clean on `main...origin/main` in all three repos. A failed switch or a broken link is not reported as "not applied": read the error, fix it, and rerun; if the fix is a decision that is his, stop and ask him interactively. Never finish with "pending", "not applied yet" or "you need to run X" - the run ends either fully applied and verified, or in a question to him.

## on a conflict (exit 3)

The script prints the repo and its unmerged files and leaves the merge in progress on `brain-sync`. Resolve each file, `git -C <repo> add` it, then run the script again; it commits the resolution, merges `main` back, pushes, deletes the branch, and continues outward.

A conflict is obvious, and resolved without asking, when one of these holds:

- The file is generated from a tracked source: take either side, then rebuild it from that source (e.g. `docs/DEV_FLOWCHART.md` -> `python3 $AAV_BRAIN/bin/store/brain-flow.py`). Merge the source, never the output.
- The file is append-only data (e.g. `*.jsonl` in `logs/`): keep both sides' lines, dropping exact duplicates, in timestamp order.
- The submodule pointer conflicts in the outer repo: take the commit the inner repo was just pushed at.
- The two sides changed different, non-overlapping lines and git only refused on proximity.
- Both sides made the same change, or one side's change plainly contains the other's.

Anything else - both sides changed the same lines of a card, a skill, a script or a config in ways that contradict, or combining them would mean guessing what he meant - STOP and ask him interactively before touching it: show the repo, the file and both hunks in plain words, and ask which to keep or how to combine them. Never pick a side silently, and never force-push.

## on a block (exit 5)

Origin could not be fetched, refused the push three times, or a stale `brain-sync` branch exists that is not checked out. The message names the repo; report it to him rather than working around it.

## rules

- Only `main` reaches `origin`; `brain-sync` is the one local branch the sync makes, and it is deleted once `main` is pushed. Never `--force`.
- The author and message are fixed: `arpadav`, `arpadav@gmail.com`, `brain-sync`.
- brain-sync always runs `home-manager switch` itself (see apply); it never hands that step back to him.
- Only two end states exist: fully pushed, merged and applied; or stopped on a conflict with a question to him. Never a status report of work left undone.
