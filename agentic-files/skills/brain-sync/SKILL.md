---
name: brain-sync
description: "Push the brain to GitHub main: its submodules (logs), the brain store, then the home-manager repo that holds it. Load this when he says 'brain-sync', 'sync the brain', 'push the brain'. Each repo's work goes through a short-lived local branch that merges main in and fast-forwards main; an obvious conflict is resolved automatically, a contradicting or intent-dependent one stops and is put to him. Afterwards the merged result is applied with `home-manager switch`, so nothing is left pulled-but-not-live."
---

# brain-sync

Push every brain repo to `main`, innermost first: the brain's submodules (e.g. `logs`), the brain store, then the home-manager repo that holds the brain. The identity and message of every commit the sync makes are the script's, and `b-sync -h` names them.

## run

```bash
b-sync -c   # optional: what each repo holds
b-sync
```

Exit 0 means every repo is on `origin/main` with the `brain-sync` branch gone. The steps each repo goes through, and every stop with its exit code, are `b-sync -h`. Relay every `b-sync: warning:` line to him.

## apply (always, after exit 0)

Pulled changes are not done until they are live. Run the same switch as the `re` alias:

```bash
home-manager switch -b backup --flake "$HOME/.config/home-manager#headless" --impure
```

Then verify: `readlink -e` every `~/.claude/skills/brain-*` link and `~/.claude/agents/brain` (none broken), `b-find` resolves, `b-walk -h` runs, and `git status -sb` is clean on `main...origin/main` in every repo `b-sync -c` lists. A failed switch or a broken link is not reported as "not applied": read the error, fix it, and rerun; if the fix is a decision that is his, stop and ask him interactively. Never finish with "pending", "not applied yet" or "you need to run X" - the run ends either fully applied and verified, or in a question to him.

## on a conflict (exit 3)

`b-sync` names the repo and its unmerged files and leaves the merge in progress on the `brain-sync` branch. Resolve each file, `git -C <repo> add` it, then run `b-sync` again; it resumes (`b-sync -h`) and continues outward.

A conflict is obvious, and resolved without asking, when one of these holds:

- The file is generated from a tracked source: take either side, then rebuild it from that source (e.g. `docs/DEV_FLOWCHART.md` -> `b-flow`). Merge the source, never the output.
- The file is append-only data (e.g. `*.jsonl` in `logs/`): keep both sides' lines, dropping exact duplicates, in timestamp order.
- The submodule pointer conflicts in the outer repo: take the commit the inner repo was just pushed at.
- The two sides changed different, non-overlapping lines and git only refused on proximity.
- Both sides made the same change, or one side's change plainly contains the other's.

Anything else - both sides changed the same lines of a principle, a skill, a script or a config in ways that contradict, or combining them would mean guessing what he meant - STOP and ask him interactively before touching it: show the repo, the file and both hunks in plain words, and ask which to keep or how to combine them. Never pick a side silently, and never force-push.

## on any other stop (exit 5)

The message names the repo and the stop (`b-sync -h` lists them), and a scan stop prints what it found. Report to him what was found; never reset, never force, and never rewrite or drop the commits a scan named - what becomes of them is his call.

## rules

- Only `origin`'s `main` is pushed; the `brain-sync` branch is the one local branch the sync makes, and it is deleted once `main` follows what origin accepted. Never `--force`.
- brain-sync always runs `home-manager switch` itself (see apply); it never hands that step back to him.
- The run ends fully pushed, merged and applied, or stopped and reported to him: a conflict (exit 3) with a question, any other stop (exit 5), a wrong command line (exit 2), or a crash (exit 1). Never a status report of work left undone.
