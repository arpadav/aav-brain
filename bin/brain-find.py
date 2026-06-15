#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""brain-find: print the discovered brain repo root, no hardcoded path.

the discovery idiom (P01-ish: never guess a path): a skill does not assume
`$AAV_BRAIN` is exported. it runs this, which locates the brain via find_brain
(this file's own location -> ~/.agents skill symlink -> ~/.claude -> the
fallback path) and prints the root, so every skill resolves the store the same
way on any machine. the brain is ONE repo: `AAV_BRAIN` is the single anchor and
the agents / skills / bin dirs all derive from it.

    python3 brain-find.py             print the aav-brain root
    python3 brain-find.py --export    print the shell `export AAV_BRAIN=...` line to eval
    python3 brain-find.py --aav       print the aav-brain root
    python3 brain-find.py --agents    print the agents dir (<root>/agentic-files/agents)
    python3 brain-find.py --skills    print the skills dir (<root>/agentic-files/skills)
    python3 brain-find.py --bin       print the bin/ dir (where the scripts live)

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import sys

from brainlib import find_brain

# --------------------------------------------------
# entrypoint
# --------------------------------------------------
def main():
    """resolve the brain root and print it in the requested form."""
    aav_brain = find_brain()
    args = sys.argv[1:]
    # --------------------------------------------------
    # selectors: one derived path, for direct substitution
    # --------------------------------------------------
    if "--aav" in args:
        print(aav_brain)
    elif "--agents" in args:
        print(aav_brain / "agentic-files" / "agents")
    elif "--skills" in args:
        print(aav_brain / "agentic-files" / "skills")
    elif "--bin" in args:
        print(aav_brain / "bin")
    # --------------------------------------------------
    # export: shell-evalable. the brain is one repo, so `AAV_BRAIN` is the single
    # irreducible anchor - bin, agents, and skills all derive from it
    # (`$AAV_BRAIN/bin`, `brain-find --agents`/`--skills`), none is its own var (P32).
    # --------------------------------------------------
    elif "--export" in args:
        print(f"export AAV_BRAIN={aav_brain}")
    # --------------------------------------------------
    # default: the root
    # --------------------------------------------------
    else:
        print(aav_brain)


if __name__ == "__main__":
    main()
