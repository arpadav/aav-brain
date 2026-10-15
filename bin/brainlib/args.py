"""brainlib.args: one parse of argv, shared by every brain tool.

the rule for what counts as a flag VALUE is applied once here rather than
re-implemented per accessor, which is what lets a decision text carrying a
flag-shaped substring survive the parse intact

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.vocab import Exit, Flag

# --------------------------------------------------
# external
# --------------------------------------------------
import sys
from dataclasses import dataclass

@dataclass(frozen=True)
class Args:
    """one parse of argv, shared by every brain tool.

    # Example

        args = Args.from_argv()
        if args.has(Flag.CHECK):
            ...
    """

    tokens: tuple[str, ...]

    @classmethod
    def from_argv(cls) -> "Args":
        """the current process arguments, without the program name.

        # Returns

        an Args over `sys.argv[1:]`
        """
        return cls(tuple(sys.argv[1:]))

    def flags(self) -> tuple[str, ...]:
        """the tokens that are FLAGS, with every flag-shaped value removed.

        a value-taking flag claims the token after it, and that token may itself
        look like a flag - a decision text, a rejected option. it is claimed
        UNLESS it is an exact member of the vocabulary, because a bare `--prune`
        sitting where a value belongs is far more likely a missing argument than
        a decision literally named `--prune`. so `--decision "--prune vs x"`
        reads as one flag with a value, while `--prune --restore TS` reads as
        two flags and leaves `--prune` without one

        # Returns

        the flag tokens, in order, values excluded

        # Example

            >>> Args(("--decision", "--prune vs --delete", "--check")).flags()
            ('--decision', '--check')
            >>> Args(("--prune", "--restore", "TS")).flags()
            ('--prune', '--restore')
        """
        return tuple(name for name, _ in self.parsed()[0])

    def parsed(self) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]]:
        """one walk of argv, split into (flag, value) pairs and positionals.

        every other reader derives from this, so the rule for what counts as a
        value is applied once rather than re-implemented per accessor

        # Returns

        a (pairs, positionals) tuple; a flag given no value pairs with `""`

        # Example

            >>> Args(("--since", "HEAD", "a.py")).parsed()
            ((('--since', 'HEAD'),), ('a.py',))
        """
        known = {member.value for member in Flag}
        valued = {member.value for member in Flag.valued()}
        pairs: list[tuple[str, str]] = []
        rest: list[str] = []
        skip = False
        for index, token in enumerate(self.tokens):
            if skip:
                skip = False
                continue
            if not token.startswith("-"):
                rest.append(token)
                continue
            following = self.tokens[index + 1] if index + 1 < len(self.tokens) else ""
            skip = token in valued and bool(following) and following not in known
            pairs.append((token, following if skip else ""))
        return tuple(pairs), tuple(rest)

    def has(self, flag: Flag) -> bool:
        """whether a flag is present in FLAG position.

        # Arguments

        * `flag` - the flag to look for

        # Returns

        true when the flag appears as a flag, never when it is only a value

        # Example

            >>> Args(("--decision", "--prune vs --delete")).has(Flag.PRUNE)
            False
            >>> Args(("--prune", "TS")).has(Flag.PRUNE)
            True
        """
        return flag.value in self.flags()

    def value(self, flag: Flag, default: str = "") -> str:
        """the value following a flag, or a default.

        # Arguments

        * `flag` - the flag whose value to read
        * `default` - returned when the flag is absent or was given no value

        # Returns

        the token after the flag's first occurrence

        # Example

            >>> Args(("--state", "IMPL")).value(Flag.STATE)
            'IMPL'
            >>> Args(("--state",)).value(Flag.STATE, "?")
            '?'
        """
        return next(iter(self.values(flag)), default)

    def values(self, flag: Flag) -> list[str]:
        """every value following each occurrence of a repeatable flag.

        # Arguments

        * `flag` - the repeatable flag

        # Returns

        one value per occurrence that HAS one, in argument order

        # Example

            >>> Args(("--principle", "P26", "--principle", "P28")).values(Flag.PRINCIPLE)
            ['P26', 'P28']
            >>> Args(("--prune", "--restore", "TS")).values(Flag.PRUNE)
            []
        """
        return [value for name, value in self.parsed()[0] if name == flag.value and value]

    def positional(self) -> list[str]:
        """the arguments that are neither a flag nor a flag's value.

        which flags consume a value is known globally, so a caller no longer
        declares its own set here and cannot disagree with the parse

        # Returns

        the positional arguments, in order

        # Example

            >>> Args(("--since", "HEAD", "a.py", "b.py")).positional()
            ['a.py', 'b.py']
        """
        return list(self.parsed()[1])

    def unknown(self, *accepted: Flag) -> list[str]:
        """the flag-shaped arguments this tool does not accept.

        # Arguments

        * `accepted` - the flags this tool understands

        # Returns

        the unrecognised flags, in order; empty when the command line is clean

        # Example

            >>> Args(("--check", "--typo")).unknown(Flag.CHECK)
            ['--typo']
            >>> Args(("--check",)).unknown(Flag.CHECK)
            []
        """
        allowed = {flag.value for flag in accepted}
        return [t for t in self.flags() if t.startswith("--") and t not in allowed]

    def starved(self, *flags: Flag) -> list[str]:
        """the given flags that are present but were handed no value.

        a value-taking flag whose value is missing is a typo, not a request:
        `--prune --restore TS` means one of the two was meant to carry the
        timestamp, and doing half of it silently is worse than refusing

        # Arguments

        * `flags` - the value-taking flags to check

        # Returns

        the flags present in flag position with no value, in order

        # Example

            >>> Args(("--prune", "--restore", "TS")).starved(Flag.PRUNE, Flag.RESTORE)
            ['--prune']
        """
        present = self.flags()
        return [flag.value for flag in flags
                if flag.value in present and not self.values(flag)]

    def gate(self, tool: str, doc: str | None, *accepted: Flag) -> None:
        """answer --help from the module docstring, then reject any unrecognised flag.

        one call is the whole command-line contract: the flags passed are both
        what the tool accepts and what it advertises, and the help text is the
        docstring the module already carries, so neither can drift from a second
        copy. every tool gates here rather than only the ones that read a flag -
        an unrecognised flag left unrejected falls through to the default
        action, which for a builder is a write to a committed artifact

        # Arguments

        * `tool` - this tool's name, for its messages
        * `doc` - the calling module's `__doc__`, printed verbatim for --help
        * `accepted` - every flag this tool understands
        """
        if self.has(Flag.HELP):
            print((doc or f"{tool}: no usage recorded").strip())
            sys.exit(Exit.OK)
        if unrecognised := self.unknown(Flag.HELP, *accepted):
            print(f"{tool}: unknown flag {unrecognised[0]}", file=sys.stderr)
            print(f"{tool}: `--help` lists what it accepts", file=sys.stderr)
            sys.exit(Exit.USAGE)
