"""brainlib.tool: how a brain tool starts and ends: argv, stdin, -h, and the exit code.

the rule for what counts as a flag VALUE, and how a short spelling resolves,
is applied once here rather than re-implemented per accessor, which is what
lets a decision text carrying a flag-shaped substring survive the parse
intact. every command's flags are declared once, in COMMANDS, which the
legend and each tool's -h row render. every tool ends through `Tool.run`, so a
code means the same thing whichever tool returned it

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.vocab import VALUE, Exit, Flag, NoVerdict, UsageError

# --------------------------------------------------
# external
# --------------------------------------------------
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from itertools import combinations
from types import MappingProxyType
from typing import NoReturn

# --------------------------------------------------
# constants
# --------------------------------------------------
# how free text reaches a tool, named once for stdin_text's refusal and the positional one
HEREDOC = "the text goes on stdin through a quoted heredoc: <<'EOF', the text, then EOF"
# the token past which every token is positional, however it is spelled
END_OF_FLAGS = "--"
# every command's flags, keyed by its command (`Layout.command`); -h is every command's and is not listed
COMMANDS: Mapping[str, tuple[Flag, ...]] = MappingProxyType({
    "b-compile": (Flag.CHECK,),
    "b-decisions": (),
    "b-extract": (Flag.OUT, Flag.ARCHIVE, Flag.ARCHIVE_DIR),
    "b-find": (Flag.EXPORT,),
    "b-flow": (Flag.CHECK, Flag.MERMAID),
    "b-fmt": (Flag.CHECK, Flag.GATE, Flag.STALE, Flag.SINCE),
    "b-gate": (Flag.SINCE, Flag.TAG, Flag.LAST),
    "b-graph": (Flag.CHECK,),
    "b-lint": (Flag.LIST, Flag.VERBOSE),
    "b-misses": (Flag.SINCE,),
    "b-open-items": (),
    "b-principles": (Flag.CHECK,),
    "b-private": (Flag.STAGING, Flag.SINCE, Flag.TIP),
    "b-recall": (Flag.COUNT, Flag.BINDS, Flag.TELLS, Flag.NEIGHBORS, Flag.ALL),
    "b-register": (),
    "b-shape": (Flag.CHECK, Flag.SINCE),
    "b-sync": (Flag.CHECK,),
    "b-trace": (Flag.SKILL, Flag.DECISION, Flag.CHOSEN, Flag.REJECT, Flag.AFFECTS, Flag.PRINCIPLE, Flag.SUPERSEDES,
                Flag.SESSION, Flag.AGAINST, Flag.STALE_CANDIDATES, Flag.PRUNE, Flag.RESTORE, Flag.PRUNED),
    "b-verify": (Flag.RUN,),
    "b-walk": (Flag.STATE, Flag.MODE, Flag.ON, Flag.DOC, Flag.LEGEND),
})


@dataclass(frozen=True)
class Args:
    """one parse of argv, shared by every brain tool.

    # Example

        def main(args: Args) -> Exit | None:
            if args.has(Flag.CHECK):
                ...
    """

    tokens: tuple[str, ...]
    # the flags the command takes, whose one-letter spellings this parse resolves; -h always resolves
    accepted: tuple[Flag, ...] = ()

    def flags(self) -> tuple[str, ...]:
        """the tokens that are FLAGS, each by its long spelling, with every flag-shaped value removed.

        a value-taking flag claims the token after it, and that token may itself
        look like a flag - a decision text, a rejected option, `-l` handed to
        `b-fmt -s`. it is claimed UNLESS it is END_OF_FLAGS, the long spelling
        of any flag, or the short spelling of a flag this command takes,
        because a bare `--prune` sitting where a value belongs is far more
        likely a missing argument than a decision literally named `--prune`.
        so `--decision "--prune vs x"` reads as one flag with a value, while
        `--prune --restore TS` reads as two flags and leaves `--prune` without
        one. every token after END_OF_FLAGS is positional

        # Returns

        the flag tokens, in order, values excluded; a token that resolves to no
        accepted flag is kept as typed, for `Tool.admit` to refuse

        # Example

            >>> Args(("--decision", "--prune vs --delete", "--check")).flags()
            ('--decision', '--check')
            >>> Args(("--prune", "--restore", "TS")).flags()
            ('--prune', '--restore')
            >>> Args(("-cv",), (Flag.CHECK, Flag.VERBOSE)).flags()
            ('--check', '--verbose')
        """
        return tuple(name for name, _ in self.parsed()[0])

    def parsed(self) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]]:
        """one walk of argv, split into (flag, value) pairs and positionals.

        every other reader derives from this, so the rule for what counts as a
        value is applied once rather than re-implemented per accessor

        # Returns

        a (pairs, positionals) tuple, each flag by its long spelling; a flag
        given no value pairs with `""`

        # Example

            >>> Args(("--since", "HEAD", "a.py")).parsed()
            ((('--since', 'HEAD'),), ('a.py',))
            >>> grammar = (Flag.CHECK, Flag.SINCE)
            >>> Args(("-s", "HEAD", "a.py"), grammar).parsed() == Args(("--since", "HEAD", "a.py")).parsed()
            True
            >>> Args(("-sHEAD",), grammar).parsed()
            ((('--since', 'HEAD'),), ())
            >>> Args(("-cs", "HEAD"), grammar).parsed()
            ((('--check', ''), ('--since', 'HEAD')), ())
            >>> Args(("-s", "-l", "-c"), grammar).parsed()
            ((('--since', '-l'), ('--check', '')), ())
            >>> Args(("-c", "--", "-x.py", "--since"), grammar).parsed()
            ((('--check', ''),), ('-x.py', '--since'))
        """
        # --------------------------------------------------
        # the letters this command resolves, and the tokens a value-taking flag never claims
        # --------------------------------------------------
        letters = {flag.short: flag for flag in (Flag.HELP, *self.accepted)}
        unclaimed = {END_OF_FLAGS, *Flag.longs(), *letters}
        # --------------------------------------------------
        # accumulators: flags with their values, and the positional words
        # --------------------------------------------------
        pairs: list[tuple[str, str]] = []
        rest: list[str] = []
        index = 0
        # --------------------------------------------------
        # walk the tokens once, a flag consuming the token after it when it takes a value
        # --------------------------------------------------
        while index < len(self.tokens):
            token = self.tokens[index]
            index += 1
            # --------------------------------------------------
            # past END_OF_FLAGS every token is positional
            # --------------------------------------------------
            if token == END_OF_FLAGS:
                rest.extend(self.tokens[index:])
                break
            # --------------------------------------------------
            # a bare word, or a lone dash, is positional
            # --------------------------------------------------
            if not token.startswith("-") or not token[1:]:
                rest.append(token)
                continue
            # --------------------------------------------------
            # every flag the token spells but the last is a switch
            # --------------------------------------------------
            *switches, last = Args.spelled(token, letters)
            pairs.extend((name, "") for name in switches)
            # --------------------------------------------------
            # the last takes an attached value, else the next token when it takes a value and that token is no flag
            # --------------------------------------------------
            if (attached := Args.attached(token, letters)) is not None:
                pairs.append((last, attached))
                continue
            following = self.tokens[index] if index < len(self.tokens) else ""
            claims = last in Flag.valued() and bool(following) and following not in unclaimed
            pairs.append((last, following if claims else ""))
            index += claims
        return tuple(pairs), tuple(rest)

    @staticmethod
    def spelled(token: str, letters: Mapping[str, Flag]) -> tuple[str, ...]:
        """the long spellings a flag-shaped token stands for.

        a long token is itself. a short one is a cluster of letters: each is a
        switch but the last, which may take a value; a value-taking letter
        first with more after it carries that rest as its value (`attached`)

        # Arguments

        * `token` - one argv token starting with a dash
        * `letters` - the command's flags by short spelling

        # Returns

        the long spellings; the token as typed when a letter is not the
        command's, or a value-taking letter sits inside a cluster, so
        `Tool.admit` can name it

        # Example

            >>> letters = {flag.short: flag for flag in (Flag.CHECK, Flag.VERBOSE, Flag.SINCE)}
            >>> [Args.spelled(token, letters) for token in ("--x", "-cv", "-sHEAD", "-cx", "-csv")]
            [('--x',), ('--check', '--verbose'), ('--since',), ('-cx',), ('-csv',)]
        """
        if token.startswith("--"):
            return (token,)
        if Args.attached(token, letters) is not None:
            return (letters[token[:2]].value,)
        flags = [flag for letter in token[1:] if (flag := letters.get(f"-{letter}")) is not None]
        if len(flags) < len(token) - 1 or any(flag.takes_value for flag in flags[:-1]):
            return (token,)
        return tuple(flag.value for flag in flags)

    @staticmethod
    def attached(token: str, letters: Mapping[str, Flag]) -> str | None:
        """the value a short token carries after its value-taking first letter: `-sHEAD` is --since HEAD.

        # Arguments

        * `token` - one argv token starting with a dash
        * `letters` - the command's flags by short spelling

        # Returns

        the rest of the token past the letter; None when the token is long,
        its first letter takes no value, nothing follows the letter, or what
        follows opens on `=`, which `Tool.refusal` names rather than storing
        `=HEAD` as the value

        # Example

            >>> letters = {flag.short: flag for flag in (Flag.CHECK, Flag.SINCE)}
            >>> [Args.attached(token, letters) for token in ("-sHEAD", "-s", "-cs", "--since", "-s=HEAD")]
            ['HEAD', None, None, None, None]
        """
        letter, rest = token[:2], token[2:]
        return (rest if rest and not rest.startswith("=") and not token.startswith("--")
                and letters.get(letter) in Flag.valued() else None)

    def asks_help(self) -> bool:
        """whether -h stands in flag position: alone, in a cluster, or beside a letter this command does not take.

        help answers an otherwise-invalid command line, so `-hZ` is help, not an unknown flag

        # Returns

        true when a flag token is --help or a short cluster carrying the letter

        # Example

            >>> grammar = (Flag.CHECK, Flag.SINCE)
            >>> [Args((token,), grammar).asks_help() for token in ("-h", "-ch", "-hZ", "-sh", "--hz")]
            [True, True, True, False, False]
        """
        letter = Flag.HELP.short.removeprefix("-")
        return any(token == Flag.HELP.value or (not token.startswith("--") and letter in token[1:])
                   for token in self.flags())

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

        >>> tool = Tool("t", "t: a tool.", flags=(Flag.CHECK, Flag.VERBOSE, Flag.SINCE, Flag.STALE),
        ...             positionals=(1, None), modes=((Flag.CHECK,), (Flag.STALE, Flag.SINCE)))
        >>> tool.admit(tool.parse(("--stale", "--since", "HEAD", "a.py")))
        >>> tool.admit(tool.parse(("-cv", "a.py")))
        >>> for argv in (("-x", "a.py"), ("-cx", "a.py"), ("-vsHEAD", "a.py"), ("a.py", "-s"), ("--check",),
        ...              ("-c", "-S", "a.py"), ("-s=HEAD", "a.py"), ("--since=HEAD", "a.py")):
        ...     try:
        ...         tool.admit(tool.parse(argv))
        ...     except UsageError as wrong:
        ...         print(wrong)
        unknown flag -x
        unknown flag -x in -cx
        ambiguous -vsHEAD: a letter that takes a value goes last, its value after it, or alone, the value attached
        -s=--since takes a value
        takes 1 to any positional argument(s), not 0
        -c=--check and -S=--stale cannot be combined
        -s=HEAD: a value follows its flag after a space, or attached to its letter, never after `=`
        --since=HEAD: a value follows its flag after a space, or attached to its letter, never after `=`
    """

    # the tool's command (`Layout.command`), for every message
    name: str
    # the script's __doc__, printed for -h
    doc: str | None
    # every flag it accepts; each one's `takes_value` says whether it takes a value
    flags: tuple[Flag, ...] = ()
    # (least, most) positional arguments; most None is no upper bound
    positionals: tuple[int, int | None] = (0, 0)
    # flag groups that each pick a mode; flags from two groups never combine
    modes: tuple[tuple[Flag, ...], ...] = ()
    # takes free text on stdin, so a stray word is refused with HEREDOC
    stdin: bool = False

    @classmethod
    def of(cls, name: str, doc: str | None, *, positionals: tuple[int, int | None] = (0, 0),
           modes: tuple[tuple[Flag, ...], ...] = (), stdin: bool = False) -> "Tool":
        """a command's contract, its flags read from COMMANDS.

        # Arguments

        * `name` - the command, `Layout.command`; a key of COMMANDS
        * `doc` - the script's __doc__
        * `positionals`, `modes`, `stdin` - as the fields of the same names

        # Returns

        the tool

        # Raises

        LookupError naming the missing row when `name` is no key of COMMANDS:
        a new script declares its flags there before it runs

        # Example

            >>> Tool.of("b-walk", None).flags == COMMANDS["b-walk"]
            True
            >>> Tool.of("b-new", None)
            Traceback (most recent call last):
            ...
            LookupError: b-new has no row in COMMANDS (bin/brainlib/tool.py); add one naming its flags
        """
        if name not in COMMANDS:
            raise LookupError(f"{name} has no row in COMMANDS (bin/brainlib/tool.py); add one naming its flags")
        return cls(name, doc, COMMANDS[name], positionals, modes, stdin)

    @staticmethod
    def legend(commands: Iterable[str] = COMMANDS) -> str:
        """every command's row under one line saying how to read them: the lookup table a session starts with.

        built from COMMANDS rather than from the scripts on disk, so a script
        with no row fails alone (`Tool.of`) and never takes the legend with it

        # Arguments

        * `commands` - the commands to list, keys of COMMANDS; every one when omitted

        # Returns

        the header line, then one row per command, sorted

        # Example

            >>> from brainlib import Layout
            >>> sorted(Layout.command(script) for script in Layout.discover().scripts) == sorted(COMMANDS)
            True
            >>> print(Tool.legend(["b-walk", "b-principles"]))
            legend: short=long, ARG takes a value, letters combine (b-shape -cs HEAD), -h=--help on every command
            b-principles -c=--check
            b-walk -s=--state ARG, -m=--mode ARG, -o=--on ARG, -d=--doc, -l=--legend
        """
        combined = f"b-shape {Flag.CHECK.short}{Flag.SINCE.short.removeprefix('-')} HEAD"
        head = (f"legend: short=long, {VALUE} takes a value, letters combine ({combined}), "
                f"{Flag.HELP.spelling} on every command")
        return "\n".join([head, *(Tool(name, None, COMMANDS[name]).row() for name in sorted(commands))])

    @staticmethod
    def clashes(commands: Mapping[str, tuple[Flag, ...]]) -> list[tuple[Flag, Flag]]:
        """the flag pairs sharing a letter where a tool taking one shares a flag with a tool taking the other.

        a shared letter is safe only between commands with nothing in common:
        anywhere else the same letter would mean two things to one reader. -h
        is every command's, so a flag taking its letter clashes everywhere

        # Arguments

        * `commands` - flags by command, COMMANDS

        # Returns

        the clashing pairs; empty when every letter is unambiguous

        # Example

            >>> Tool.clashes(COMMANDS)
            []
            >>> Tool.clashes({"a": (Flag.SINCE, Flag.CHECK), "b": (Flag.STATE, Flag.CHECK)})
            [(<Flag.SINCE: '--since'>, <Flag.STATE: '--state'>)]
        """
        takers = {flag: [set(flags) for flags in commands.values() if flag in flags] for flag in Flag}
        return [(one, other) for one, other in combinations(Flag, 2)
                if one.short == other.short
                and ((Flag.HELP in (one, other) and any(takers[one] + takers[other]))
                     or any(mine & theirs for mine in takers[one] for theirs in takers[other]))]

    def row(self) -> str:
        """this command's flags, short=long, value-taking ones marked VALUE.

        # Returns

        the command, then its flags; the command alone when it takes none

        # Example

            >>> Tool("b-gate", None, (Flag.SINCE, Flag.LAST)).row()
            'b-gate -s=--since ARG, -l=--last'
        """
        spellings = ", ".join(f"{flag.spelling} {VALUE}" if flag.takes_value else flag.spelling
                              for flag in self.flags)
        return f"{self.name} {spellings}".rstrip()

    def parse(self, argv: Iterable[str]) -> Args:
        """read a command line against this tool's flags.

        # Arguments

        * `argv` - the arguments after the command

        # Returns

        the parse, its short spellings resolved to this tool's flags
        """
        return Args(tuple(argv), self.flags)

    def run(self, body: Callable[[Args], Exit | None]) -> NoReturn:
        """parse argv, answer -h, admit the command line, run the body, and exit with its verdict.

        nothing beyond the two refusals is caught: a crash keeps python's
        traceback and exits 1, which is Exit.FAILED

        # Arguments

        * `body` - the tool's main; None from it is Exit.OK

        # Returns

        never returns: the process exits with the body's `Exit`, or with the
        refusal's exit when argv or the command line is not admitted
        """
        # --------------------------------------------------
        # read the command line
        # --------------------------------------------------
        args = self.parse(sys.argv[1:])
        try:
            # --------------------------------------------------
            # help answers before any validation, so it works with otherwise-invalid arguments
            # --------------------------------------------------
            if args.asks_help():
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
            print(f"{self.name}: {wrong}; `{Flag.HELP.short}` lists what it accepts", file=sys.stderr)
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
        """the row, the docstring, then the exit-code legend generated from Exit.

        # Returns

        the tool's row, its docstring (or a placeholder naming the tool when it
        has none), a blank line, then one line listing every exit code and its name

        # Example

            >>> print(Tool("t", "t: a tool.", (Flag.CHECK,)).usage())
            t -c=--check
            t: a tool.
            <BLANKLINE>
            exit: 0 OK, 1 FAILED, 2 USAGE, 3 CONFLICT, 4 FINDINGS, 5 BLOCKED
        """
        # --------------------------------------------------
        # the exit-code legend appended to the docstring
        # --------------------------------------------------
        legend = ", ".join(f"{code.value} {code.name}" for code in Exit)
        return f"{self.row()}\n{(self.doc or f'{self.name}: no usage recorded').strip()}\n\nexit: {legend}"

    def refusal(self, token: str) -> str:
        """why a flag-shaped token resolved to none of this tool's flags.

        # Arguments

        * `token` - the token as typed, `Args.flags` keeps it so

        # Returns

        that a value-taking flag's value follows `=`, in either spelling; else
        the token when it is one flag; else that a value-taking letter sits
        inside the cluster, when every letter before it is this tool's; else
        the first letter this tool does not take
        """
        letters = {flag.short: flag for flag in (Flag.HELP, *self.flags)}
        named, equals, _ = token.partition("=")
        spelled = {flag.value: flag for flag in self.flags} | letters
        if equals and (flag := spelled.get(named)) is not None and flag.takes_value:
            return f"{token}: a value follows its flag after a space, or attached to its letter, never after `=`"
        if token.startswith("--") or not token[2:]:
            return f"unknown flag {token}"
        flags = [letters.get(f"-{letter}") for letter in token[1:]]
        valued = next((at for at, flag in enumerate(flags) if flag in Flag.valued()), None)
        if valued is not None and None not in flags[:valued]:
            return (f"ambiguous {token}: a letter that takes a value goes last, its value after it, "
                    "or alone, the value attached")
        stray = next((f"-{letter}" for letter, flag in zip(token[1:], flags, strict=True) if flag is None), token)
        return f"unknown flag {stray} in {token}"

    def admit(self, args: Args) -> None:
        """refuse a command line this tool does not accept, before its body runs.

        # Arguments

        * `args` - the command line to check against this tool's declared flags,
          positional count and modes

        # Raises

        UsageError, in this order: a flag-shaped token that is none of `flags`,
        one dash or two, so a `-h`-class typo cannot fall through to the
        default action; a declared value-taking flag given no value; a
        positional count outside `positionals`; flags from two `modes` groups
        """
        # --------------------------------------------------
        # refuse a flag this tool does not declare
        # --------------------------------------------------
        accepted = {flag.value for flag in self.flags}
        if unknown := [token for token in args.flags() if token not in accepted]:
            raise UsageError(self.refusal(unknown[0]))
        # --------------------------------------------------
        # refuse a valued flag with nothing after it
        # --------------------------------------------------
        if starved := [flag for flag in self.flags
                       if flag.takes_value and args.has(flag) and not args.values(flag)]:
            raise UsageError(f"{starved[0].spelling} takes a value")
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
            raise UsageError(f"{' and '.join(flag.spelling for flag in picked)} cannot be combined")
