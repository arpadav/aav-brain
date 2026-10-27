---
name: brain-sync
description: "Push the brain to GitHub main: its submodules (logs), the brain store, then the home-manager repo that holds it - all as arpadav, message brain-sync. Load this when he says 'brain-sync', 'sync the brain', 'push the brain'. A rejected push pulls and merges; an obvious conflict is resolved automatically, anything else is put to him."
---

# brain-sync

Push every brain repo to `main`, innermost first: the brain's submodules (e.g. `logs`), the brain store, then the home-manager repo that holds the brain. Each commit is authored `arpadav <arpadav@gmail.com>` with the message `brain-sync` and nothing else.

## run

```bash
eval "$(brain-find --export)"
python3 $AAV_BRAIN/bin/run/brain-sync.py --check   # optional: what each repo holds
python3 $AAV_BRAIN/bin/run/brain-sync.py
```

The script commits everything, pushes, and on a rejected push fetches and merges `origin/main` (also `brain-sync`) and pushes again. Exit 0 means every repo is on `origin/main`.

## on a conflict (exit 3)

The script prints the repo and its unmerged files and leaves the merge in progress. Resolve each file, `git -C <repo> add` it, then run the script again; it finishes the merge and continues outward.

A conflict is obvious, and resolved without asking, when one of these holds:

- The file is generated: rebuild it from its source instead of merging (e.g. `brain/graph/graph.json` -> `python3 $AAV_BRAIN/bin/store/brain-graph.py`).
- The file is append-only data (e.g. `*.jsonl` in `logs/`): keep both sides' lines, dropping exact duplicates, in timestamp order.
- The submodule pointer conflicts in the outer repo: take the commit the inner repo was just pushed at.
- The two sides changed different, non-overlapping lines and git only refused on proximity.

Anything else - a card, a skill, a script or a config where both sides changed the same lines - goes to him: show the repo, the file and both hunks in plain words, and ask which to keep or how to combine them. Never pick a side silently, and never force-push.

## rules

- Only `main`, only `origin`. Never `--force`.
- The author and message are fixed: `arpadav`, `arpadav@gmail.com`, `brain-sync`.
- A new skill appears in `~/.claude/skills` only after `home-manager switch`; brain-sync does not run it.
