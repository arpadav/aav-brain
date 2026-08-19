#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-find: print the discovered brain repo root, no hardcoded path.

the discovery idiom (P01-ish: never guess a path): a skill does not assume
`$AAV_BRAIN` is exported. it runs this, which locates the brain via find_brain
(this file's own location -> the ~/.agents skill symlink -> ~/.claude) and prints
the root, so every skill resolves the store the same way on any machine. there is
deliberately NO hardcoded-path fallback - a guess at a conventional checkout would
resolve a STALE sibling, so discovery fails loud instead (P32). the brain is ONE
repo: `AAV_BRAIN` is the single anchor and the agents / skills / bin dirs all
derive from it

    python3 brain-find.py             print the aav-brain root
    python3 brain-find.py --export    print the shell `export AAV_BRAIN=...` line to eval
    python3 brain-find.py --agents    print the agents dir (<root>/agentic-files/agents)
    python3 brain-find.py --skills    print the skills dir (<root>/agentic-files/skills)
    python3 brain-find.py --bin       print the bin/ dir (where the scripts live)

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Env, Flag, Layout

# --------------------------------------------------
# external
# --------------------------------------------------
import sys
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem

def main() -> None:
    """resolve the brain root and print it in the requested form."""
    layout = Layout.discover()
    args = Args.from_argv()
    # --------------------------------------------------
    # selectors: one derived path, for direct substitution. the root itself has no
    # flag - it is the default, and a second spelling for it would be two ways to
    # ask one question
    # --------------------------------------------------
    selectors = {Flag.AGENTS: layout.agents, Flag.SKILLS: layout.skills, Flag.BIN: layout.bin}
    if unknown := args.unknown(Flag.EXPORT, *selectors):
        sys.exit(f"{TOOL}: unknown flag {unknown[0]}")
    for flag, path in selectors.items():
        if args.has(flag):
            print(path)
            return
    # --------------------------------------------------
    # export: shell-evalable. the brain is one repo, so `AAV_BRAIN` is the single
    # irreducible anchor - bin, agents, and skills all derive from it
    # (`$AAV_BRAIN/bin`, `brain-find --agents`/`--skills`), none is its own var (P32)
    # --------------------------------------------------
    if args.has(Flag.EXPORT):
        print(f"export {Env.AAV_BRAIN}={layout.root}")
    else:
        print(layout.root)


if __name__ == "__main__":
    main()
