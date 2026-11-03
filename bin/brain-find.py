#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""b-find: print the discovered brain repo root, no hardcoded path.

every command finds the root from its own location (P32). home-manager
exports it as `$AAV_BRAIN` and its short alias `$AVB`, which the skills and
agents read brain files off; this prints the root `find_brain` discovers, or
the line that exports both, for a shell that has neither

    b-find       print the aav-brain root
    b-find -e    print the shell `export AAV_BRAIN=... AVB=...` line to eval

Author: aav
"""
# brainlib lives in bin/, beside this script; `python -I` leaves the script's dir off sys.path
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Env, Flag, Layout, Tool

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages
TOOL = Layout.command(Path(__file__))


def main(args: Args) -> None:
    """print the brain root, or under `-e` the line that exports it.

    # Arguments

    * `args` - the parsed command line; `-e` picks the export line
    """
    # --------------------------------------------------
    # discover the root, then print it bare or as the export line
    # --------------------------------------------------
    root = str(Layout.discover().root)
    print(Env.export(root, Env.AAV_BRAIN, Env.AVB) if args.has(Flag.EXPORT) else root)


if __name__ == "__main__":
    Tool.of(TOOL, __doc__).run(main)
