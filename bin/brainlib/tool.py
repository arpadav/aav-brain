"""brainlib.tool: how a brain tool starts and ends: argv, stdin, --help, and the exit code.

the rule for what counts as a flag VALUE is applied once here rather than
re-implemented per accessor, which is what lets a decision text carrying a
flag-shaped substring survive the parse intact. every tool ends through
`Tool.run`, so a code means the same thing whichever tool returned it

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
from collections.abc import Callable
from dataclasses import dataclass
from typing import NoReturn

# --------------------------------------------------
# constants
# --------------------------------------------------
# the spellings that ask for the docstring
HELP = (Flag.HELP, Flag.HELP_SHORT)
# how free text reaches a tool, named once for stdin_text's refusal and the positional one
HEREDOC = "the text goes on stdin through a quoted heredoc: <<'EOF', the text, then EOF"


class UsageError(Exception):
    """the command line is wrong; Tool.run prints it once and exits Exit.USAGE."""


# N818 wants an `Error` suffix; nothing here erred, the tool could not look, and the name says that
class NoVerdict(Exception):  # noqa: N818
    """the tool could not look, so it has no verdict; Tool.run prints it once and exits Exit.FAILED."""


@dataclass(frozen=True)
class Args:
    """one parse of argv, shared by every brain tool.

    # Example

        def main(args: Args) -> Exit | None:
            if args.has(Flag.CHECK):
                ...
    """

    tokens: tuple[str, ...]

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
        # --------------------------------------------------
        # the spellings a token can be checked against, and which of them take a value
        # --------------------------------------------------
        known = {member.value for member in Flag}
        valued = {member.value for member in Flag.valued()}
        # --------------------------------------------------
        # accumulators: flags with their values, and the positional words
        # --------------------------------------------------
        pairs: list[tuple[str, str]] = []
        rest: list[str] = []
        skip = False
        # --------------------------------------------------
        # walk the tokens once, a flag consuming the token after it when it takes a value
        # --------------------------------------------------
        for index, token in enumerate(self.tokens):
            if skip:
                skip = False
                continue
            # --------------------------------------------------
            # a bare word is positional
            # --------------------------------------------------
            if not token.startswith("-"):
                rest.append(token)
                continue
            # --------------------------------------------------
            # a flag takes the next token as its value only when it is a valued flag and that token is not itself a flag
            # --------------------------------------------------
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

        which flags consume a value is known globally, so a caller cannot
        disagree with the parse

        # Returns

        the positional arguments, in order

        # Example

            >>> Args(("--since", "HEAD", "a.py", "b.py")).positional()
            ['a.py', 'b.py']
        """
        return list(self.parsed()[1])

    def stdin_text(self) -> str:
        r"""the free text a tool takes on stdin, its whitespace folded to single spaces.

        free text never travels in argv: the shell parses an argument, and the
        one construct that parses nothing is a quoted heredoc

        # Returns

        the text

        # Raises

        UsageError with HEREDOC when stdin is a terminal (no heredoc was given)
        or carries only whitespace

        # Example

            >>> import io
            >>> from unittest import mock
            >>> with mock.patch.object(sys, "stdin", io.StringIO("  rust review,\n dont commit ")):
            ...     Args(()).stdin_text()
            'rust review, dont commit'
        """
        # --------------------------------------------------
        # a terminal has no piped text; otherwise collapse the whitespace to one line
        # --------------------------------------------------
        text = "" if sys.stdin.isatty() else " ".join(sys.stdin.read().split())
        # --------------------------------------------------
        # no text at all is a usage error that shows the heredoc spelling
        # --------------------------------------------------
        if not text:
            raise UsageError(HEREDOC)
        return text


@dataclass(frozen=True)
class Tool:
    """one tool's command-line contract, and the one way any brain tool ends.

    # Example

        >>> tool = Tool("t", "t: a tool.", flags=(Flag.CHECK, Flag.SINCE, Flag.STALE),
        ...             positionals=(1, None), modes=((Flag.CHECK,), (Flag.STALE, Flag.SINCE)))
        >>> tool.admit(Args(("--stale", "--since", "HEAD", "a.py")))
        >>> for argv in (("-x", "a.py"), ("a.py", "--since"), ("--check",), ("--check", "--stale", "a.py")):
        ...     try:
        ...         tool.admit(Args(argv))
        ...     except UsageError as wrong:
        ...         print(wrong)
        unknown flag -x
        --since takes a value
        takes 1 to any positional argument(s), not 0
        --check and --stale cannot be combined
    """

    # the script's stem, for every message
    name: str
    # the script's __doc__, printed for --help / -h
    doc: str | None
    # every flag it accepts; Flag.valued() says which take a value
    flags: tuple[Flag, ...] = ()
    # (least, most) positional arguments; most None is no upper bound
    positionals: tuple[int, int | None] = (0, 0)
    # flag groups that each pick a mode; flags from two groups never combine
    modes: tuple[tuple[Flag, ...], ...] = ()
    # takes free text on stdin, so a stray word is refused with HEREDOC
    stdin: bool = False

    def run(self, body: Callable[[Args], Exit | None]) -> NoReturn:
        """parse argv, answer --help, admit the command line, run the body, and exit with its verdict.

        nothing beyond the two refusals is caught: a crash keeps python's
        traceback and exits 1, which is Exit.FAILED

        # Arguments

        * `body` - the tool's main; None from it is Exit.OK
        """
        # --------------------------------------------------
        # read the command line
        # --------------------------------------------------
        args = Args(tuple(sys.argv[1:]))
        try:
            # --------------------------------------------------
            # help answers before any validation, so it works with otherwise-invalid arguments
            # --------------------------------------------------
            if any(args.has(flag) for flag in HELP):
                print(self.usage())
                code = Exit.OK
            else:
                # --------------------------------------------------
                # a valid invocation runs the body; its return, if any, is the exit code
                # --------------------------------------------------
                self.admit(args)
                code = body(args) or Exit.OK
        # --------------------------------------------------
        # a refused invocation says why and where the rules are
        # --------------------------------------------------
        except UsageError as wrong:
            print(f"{self.name}: {wrong}; `--help` lists what it accepts", file=sys.stderr)
            code = Exit.USAGE
        # --------------------------------------------------
        # a tool that could not look fails without implying a verdict
        # --------------------------------------------------
        except NoVerdict as blind:
            print(f"{self.name}: {blind}", file=sys.stderr)
            code = Exit.FAILED
        # --------------------------------------------------
        # exit with the code the branch above chose
        # --------------------------------------------------
        sys.exit(code)  # noqa: TID251 - the one exit every brain tool ends through

    def usage(self) -> str:
        """the docstring, then the exit-code legend generated from Exit.

        # Returns

        the tool's docstring (or a placeholder naming the tool when it has none),
        a blank line, then one line listing every exit code and its name

        # Example

            >>> print(Tool("t", "t: a tool.").usage())
            t: a tool.
            <BLANKLINE>
            exit: 0 OK, 1 FAILED, 2 USAGE, 3 CONFLICT, 4 FINDINGS, 5 BLOCKED
        """
        # --------------------------------------------------
        # the exit-code legend appended to the docstring
        # --------------------------------------------------
        legend = ", ".join(f"{code.value} {code.name}" for code in Exit)
        return f"{(self.doc or f'{self.name}: no usage recorded').strip()}\n\nexit: {legend}"

    def admit(self, args: Args) -> None:
        """refuse a command line this tool does not accept, before its body runs.

        # Arguments

        * `args` - the command line to check against this tool's declared flags,
          positional count and modes

        # Raises

        UsageError, in this order: a flag-shaped token not in `flags`, one dash
        or two, so a `-h`-class typo cannot fall through to the default action;
        a declared value-taking flag given no value; a positional count outside
        `positionals`; flags from two `modes` groups
        """
        # --------------------------------------------------
        # refuse a flag this tool does not declare
        # --------------------------------------------------
        accepted = {flag.value for flag in self.flags}
        if unknown := [token for token in args.flags() if token not in accepted]:
            raise UsageError(f"unknown flag {unknown[0]}")
        # --------------------------------------------------
        # refuse a valued flag with nothing after it
        # --------------------------------------------------
        if starved := [flag for flag in self.flags
                       if flag in Flag.valued() and args.has(flag) and not args.values(flag)]:
            raise UsageError(f"{starved[0]} takes a value")
        # --------------------------------------------------
        # refuse a positional count outside the declared bounds
        # --------------------------------------------------
        words, (least, most) = args.positional(), self.positionals
        if len(words) < least or (most is not None and len(words) > most):
            span = f"{least}" if least == most else f"{least} to {'any' if most is None else most}"
            raise UsageError(f"unexpected {words[0]!r}; {HEREDOC}" if self.stdin
                             else f"takes {span} positional argument(s), not {len(words)}")
        # --------------------------------------------------
        # refuse flags from two mode groups together
        # --------------------------------------------------
        picked = [next(flag for flag in group if args.has(flag)) for group in self.modes
                  if any(args.has(flag) for flag in group)]
        if len(picked) > 1:
            raise UsageError(f"{' and '.join(picked)} cannot be combined")
