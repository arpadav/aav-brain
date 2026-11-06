#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""b-try: run one command from the edit brain, so a brain change is tried before any other project sees it.

every other `b-*` runs from the install copy. this runs the edit copy's
script for `b-<name>` instead, named as `<name>` or `b-<name>`, found among
that brain's scripts by the rule module.nix makes commands by, so a new or
moved script is tried before it has a command of its own. everything after
the name goes to that script unparsed, `-h` included; only a bare `b-try` or
`b-try -h` is b-try's own, and a flag with anything after it names no command,
so it is refused. the script runs under `python3 -I` in this process's place,
so its exit code is b-try's

    b-try walk -s PLAN -m build    the edit brain's b-walk, given `-s PLAN -m build`
    b-try walk -h                  the edit brain's b-walk help
    b-try -h walk                  refuse: the command comes first
    b-try                          refuse, listing the edit brain's commands

no edit copy: exits FAILED, naming /home-setup

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import COMMAND_PREFIX, ISOLATED, Args, Layout, Tool, UsageError, XdgLayout

# --------------------------------------------------
# external
# --------------------------------------------------
import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import NoReturn

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages
TOOL = Layout.command(Path(__file__))


@dataclass(frozen=True)
class Trial:
    """one command line given to b-try: its own leading token, and the tail it hands the target unparsed.

    # Example

        >>> trial = Trial.of(["b-walk", "-s", "PLAN", "-h"])
        >>> trial.own, trial.tail
        (('b-walk',), ('-s', 'PLAN', '-h'))
    """

    # b-try's own command line: the command name, a flag alone, or nothing
    own: tuple[str, ...]
    # every token after it, the target's; the whole line when a flag opens it and more follows
    tail: tuple[str, ...]

    @classmethod
    def of(cls, argv: Sequence[str]) -> "Trial":
        """split a command line before anything parses it: the first token is b-try's, the rest the target's.

        a flag that opens the line with more after it names no command, so
        none of the line is b-try's own: `exec` refuses it, where `-h` would
        otherwise answer help and drop the rest unread

        # Arguments

        * `argv` - the arguments after `b-try`

        # Returns

        the trial; `own` is empty for a bare `b-try` and for a flag with a tail

        # Example

            >>> Trial.of(["walk", "-s", "X"])
            Trial(own=('walk',), tail=('-s', 'X'))
            >>> Trial.of(["walk", "-h"]).tail, Trial.of(["-h"]), Trial.of([])
            (('-h',), Trial(own=('-h',), tail=()), Trial(own=(), tail=()))
            >>> Trial.of(["-h", "walk"])
            Trial(own=(), tail=('-h', 'walk'))
        """
        own, tail = tuple(argv[:1]), tuple(argv[1:])
        if own and own[0].startswith("-") and tail:
            return cls((), own + tail)
        return cls(own, tail)

    def exec(self, args: Args) -> NoReturn:
        """replace this process with the edit brain's script for the name in `args`, given the tail.

        the name is taken with or without COMMAND_PREFIX, so `walk` and
        `b-walk` both name `b-walk`

        # Arguments

        * `args` - b-try's own parse: at most the command name

        # Returns

        never returns: the target runs in this process's place and its exit is b-try's

        # Raises

        UsageError when a flag opens the line with more after it;
        EditCopyMissing when there is no edit copy; UsageError, listing the
        edit brain's commands, when the name is missing or names none of them

        # Example

            >>> try:
            ...     Trial.of(["-h", "walk"]).exec(Args((), ()))
            ... except UsageError as wrong:
            ...     print(wrong)
            -h walk: the command comes first, then its flags (b-try walk -h)
        """
        # --------------------------------------------------
        # a flag before any command: nothing to run, and nothing of it is b-try's
        # --------------------------------------------------
        if not self.own and self.tail:
            raise UsageError(f"{' '.join(self.tail)}: the command comes first, then its flags ({TOOL} walk -h)")
        # --------------------------------------------------
        # the edit brain's script for the name, else a refusal naming what it has
        # --------------------------------------------------
        layout = Layout(XdgLayout.edit_brain())
        name = next(iter(args.positional()), None)
        command = None if name is None else f"{COMMAND_PREFIX}{name.removeprefix(COMMAND_PREFIX)}"
        if command is None or (script := layout.script_for(command)) is None:
            asked = "name a command" if command is None else f"{command} is no command"
            commands = ", ".join(map(Layout.command, layout.scripts))
            raise UsageError(f"{asked}; the edit brain {layout.root} has {commands}")
        # --------------------------------------------------
        # run it under the flag every command runs with
        # --------------------------------------------------
        # S606: the argv is this interpreter and a script of the edit brain, with no shell to inject into
        os.execv(sys.executable, (sys.executable, ISOLATED, str(script), *self.tail))  # noqa: S606


if __name__ == "__main__":
    trial = Trial.of(sys.argv[1:])
    Tool.of(TOOL, __doc__, positionals=(0, 1)).run(trial.exec, trial.own)
