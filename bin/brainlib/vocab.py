"""brainlib.vocab: the closed vocabularies every brain tool shares, and the two errors a tool ends on.

a name spelled at its call site is a literal the reader cannot grep for and
the type checker cannot see. every enum here exists so a rename is one edit
and the set a tool depends on is a list rather than an archaeology exercise.
UsageError and NoVerdict live here, below every other module, so a library
layer raises them without importing the command-line layer that reports them

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import os
import shlex
from enum import IntEnum, StrEnum
from functools import cache
from pathlib import Path
from typing import Self

# --------------------------------------------------
# constants
# --------------------------------------------------
# every file this repo reads or writes is text in this encoding, so the argument
# is a property of the repo rather than of any one call site
ENCODING = "utf-8"

# the interpreter floor. the checkers are pinned to it here; the same number is
# declared to each tool in its own config (ruff target-version, ty python-version,
# mypy python_version, pyright pythonVersion) and to `uv run` by the script headers
PYTHON_VERSION = "3.12"

# what the legend and a -h row print after a flag whose value is the token after it
VALUE = "ARG"

# the seconds a git listing or lookup may run before it counts as failed
GIT_TIMEOUT = 10
# the seconds a git command may run that writes the tree or a ref, or reads a whole
# range or every submodule: a commit, a merge, a recursive status, a patch log
LONG_GIT_TIMEOUT = 120

# a principle's yaml header: scalars and lists, keyed by field name. the shape the
# parser in brainlib.text returns and every principle reader consumes
type Frontmatter = dict[str, str | list[str]]


class UsageError(Exception):
    """the command line is wrong; Tool.run prints it once and exits Exit.USAGE."""


# N818 wants an Error suffix; nothing here erred, the tool could not look, and the name says that
class NoVerdict(Exception):  # noqa: N818
    """the tool could not look, so it has no verdict; Tool.run prints it once and exits Exit.FAILED."""


class Kind(StrEnum):
    """the two kinds the store holds, a principle and an interest, with the ordering derived from them.

    the rank is the tie-break shared by the graph build and recall.
    """

    PRINCIPLE = "principle"
    INTEREST = "interest"

    @property
    def rank(self) -> int:
        """this kind's sort position.

        # Returns

        0 for a principle, 1 for an interest

        # Example

            >>> Kind.PRINCIPLE.rank < Kind.INTEREST.rank
            True
        """
        return list(Kind).index(self)


class Rel(StrEnum):
    """every derived relationship an edge can carry, named once.

    the graph's edge vocabulary is closed and derived - never authored - so it
    belongs here rather than in the builder that writes it and again in the
    reader that traverses it
    """

    RELATES = "relates"
    TENSION = "tension"


class Tier(StrEnum):
    """how a principle reaches an agent: always, by score, or by a lower bar.

    CONSTITUTION principles skip scoring and load on every recall, CONDITIONAL principles
    are scored, NARROW principles clear a lower bar. the split is measured, not
    asserted: tiers.toml holds the rule, its thresholds, the measurement and the
    caveats behind every assignment
    """

    CONSTITUTION = "constitution"
    CONDITIONAL = "conditional"
    NARROW = "narrow"


class Confidence(StrEnum):
    """how strong the evidence behind a principle is, per schema/principle.md.

    # Example

        >>> Confidence("very-high")
        <Confidence.VERY_HIGH: 'very-high'>
    """

    VERY_HIGH = "very-high"
    HIGH = "high"
    MEDIUM = "medium"


class Env(StrEnum):
    """every environment variable the brain reads or exports, named once.

    a variable name spelled at its call site is a literal the reader cannot
    grep for and the type checker cannot see. reading through the member means
    a rename is one edit, and the set of variables the brain depends on is a
    list rather than an archaeology exercise
    """

    # the brain root home-manager exports; the flake reads it at switch time
    AAV_BRAIN = "AAV_BRAIN"
    # its short alias, for his shell and the skills' and agents' text
    AVB = "AVB"
    # the data root the brain's private state sits under
    XDG_DATA_HOME = "XDG_DATA_HOME"
    # the config root his private.toml sits under
    XDG_CONFIG_HOME = "XDG_CONFIG_HOME"
    # the claude session a call runs in, which keys its session log
    SESSION_ID = "CLAUDE_CODE_SESSION_ID"

    def read(self, default: str = "") -> str:
        """this variable's value, else a default.

        # Arguments

        * `default` - returned when the variable is unset or empty

        # Returns

        the variable's value

        # Example

            >>> import os
            >>> from unittest import mock
            >>> with mock.patch.dict(os.environ, {Env.XDG_DATA_HOME: ""}, clear=True):
            ...     Env.XDG_DATA_HOME.read("unset")
            ...     os.environ[Env.XDG_DATA_HOME] = "/srv/data"
            ...     Env.XDG_DATA_HOME.read("unset")
            'unset'
            '/srv/data'
        """
        return os.environ.get(self.value, "") or default

    @staticmethod
    def export(value: str, *names: "Env") -> str:
        """the shell line that sets each named variable to one value.

        # Arguments

        * `value` - the value every name gets, shell-quoted
        * `names` - the variables to set, in order

        # Returns

        `export NAME=value OTHER=value`

        # Example

            >>> Env.export("/srv/brain", Env.AAV_BRAIN, Env.AVB)
            'export AAV_BRAIN=/srv/brain AVB=/srv/brain'
            >>> Env.export("/srv/my brain", Env.AAV_BRAIN)
            "export AAV_BRAIN='/srv/my brain'"
        """
        return "export " + " ".join(f"{env}={shlex.quote(value)}" for env in names)

    def directory(self, fallback: Path) -> Path:
        """this variable as a directory, `~` expanded; the fallback when it is unset or relative.

        the XDG base-directory spec says a relative value is invalid and is
        ignored, so a stray `XDG_DATA_HOME=data` never lands a file under the cwd

        # Arguments

        * `fallback` - the directory the variable defaults to

        # Returns

        the variable's value as an absolute path, or `fallback`

        # Example

            >>> import os
            >>> from unittest import mock
            >>> with mock.patch.dict(os.environ, {Env.XDG_DATA_HOME: "relative/data"}):
            ...     Env.XDG_DATA_HOME.directory(Path("/fallback"))
            PosixPath('/fallback')
            >>> with mock.patch.dict(os.environ, {Env.XDG_DATA_HOME: "/srv/data"}):
            ...     Env.XDG_DATA_HOME.directory(Path("/fallback"))
            PosixPath('/srv/data')
        """
        # --------------------------------------------------
        # an unset variable reads as empty, which resolves to the current directory and is not absolute
        # --------------------------------------------------
        value = Path(self.read()).expanduser()
        # --------------------------------------------------
        # only an absolute path is honoured, per the XDG rule that a relative one is invalid
        # --------------------------------------------------
        return value if value.is_absolute() else fallback


class Flag(StrEnum):
    """every command-line flag the brain tools accept, named once with both its spellings.

    a flag spelled as a literal at each site hides a typo in one comparison, and
    the set a tool accepts is recoverable only by grep. as members they are
    enumerable, which is what lets `Tool.admit` reject a misspelled flag
    instead of ignoring it. a member's value is its long spelling, `short` its
    one-letter one; the long one is what every reader compares against, so
    `Args` resolves a short spelling to its member before anything reads it

    a letter means one flag inside any one tool, and two flags share a letter
    only when no tool taking the one shares a flag with a tool taking the other
    (`Tool.clashes`, a doctest over every command), so `-s` is --since wherever
    --since is, and --state or --session only in a tool that has nothing else in
    common. -h is every command's, so no other flag takes its letter

    a member is its long spelling, its letter, then VALUE when the token after
    it is its value; a member without the third is a bare switch

    # Example

        >>> Flag.CHECK.value, Flag.CHECK.short
        ('--check', '-c')
    """

    # the one-letter spelling: a dash, then the letter
    short: str
    # whether the token after the flag is its value
    takes_value: bool

    AFFECTS = "--affects", "a", VALUE
    AGAINST = "--against", "g"
    ALL = "--all", "a"
    ARCHIVE = "--archive", "a"
    ARCHIVE_DIR = "--archive-dir", "d", VALUE
    BINDS = "--binds", "b", VALUE
    CHECK = "--check", "c"
    CHOSEN = "--chosen", "c", VALUE
    COUNT = "--count", "n", VALUE
    DECISION = "--decision", "d", VALUE
    DOC = "--doc", "d"
    EXPORT = "--export", "e"
    GATE = "--gate", "g"
    HELP = "--help", "h"
    LAST = "--last", "l"
    LEGEND = "--legend", "l"
    LIST = "--list", "l"
    MERMAID = "--mermaid", "m"
    MODE = "--mode", "m", VALUE
    NEIGHBORS = "--neighbors", "e", VALUE
    ON = "--on", "o", VALUE
    OUT = "--out", "o", VALUE
    PRINCIPLE = "--principle", "p", VALUE
    PRUNE = "--prune", "x", VALUE
    PRUNED = "--pruned", "l"
    REJECT = "--reject", "r", VALUE
    RESTORE = "--restore", "b", VALUE
    RUN = "--run", "r"
    SESSION = "--session", "s", VALUE
    SINCE = "--since", "s", VALUE
    SKILL = "--skill", "k", VALUE
    STAGING = "--staging", "i"
    STALE = "--stale", "S"
    STALE_CANDIDATES = "--stale-candidates", "S"
    STATE = "--state", "s", VALUE
    SUPERSEDES = "--supersedes", "u", VALUE
    TAG = "--tag", "t", VALUE
    TELLS = "--tells", "t"
    TIP = "--tip", "T", VALUE
    VERBOSE = "--verbose", "v"

    def __new__(cls, long: str, letter: str, value: str = "") -> Self:
        """a member from its two spellings, the long one its value, and whether it takes a value.

        # Arguments

        * `long` - the `--name` spelling
        * `letter` - the one letter of the short spelling
        * `value` - VALUE when the token after the flag is its value

        # Returns

        the new member: a `str` equal to `long`, with `short` set to `-letter`
        and `takes_value` true exactly when `value` is VALUE
        """
        member = str.__new__(cls, long)
        member._value_ = long
        member.short = f"-{letter}"
        member.takes_value = value == VALUE
        return member

    @property
    def spelling(self) -> str:
        """both spellings, short first, as the legend and every message print them.

        # Returns

        `-s=--since`

        # Example

            >>> Flag.SINCE.spelling
            '-s=--since'
        """
        return f"{self.short}={self.value}"

    @classmethod
    @cache
    def valued(cls) -> frozenset["Flag"]:
        """every flag whose meaning is the token after it, collected once.

        knowing this globally is what lets `Args` tell a FLAG from a flag-shaped
        VALUE. without it `--decision "--prune vs --delete"` reads as a request
        to prune, and `--prune --restore TS` reads `--restore` as the timestamp
        to prune and pins the entry instead

        # Returns

        the members whose `takes_value` is set; every other member is a bare switch

        # Example

            >>> Flag.DECISION in Flag.valued(), Flag.CHECK in Flag.valued(), "--since" in Flag.valued()
            (True, False, True)
        """
        return frozenset(flag for flag in cls if flag.takes_value)

    @classmethod
    @cache
    def longs(cls) -> frozenset[str]:
        """every long spelling, collected once.

        # Returns

        `--check`, `--since`, ... for every member

        # Example

            >>> "--since" in Flag.longs(), "-s" in Flag.longs()
            (True, False)
        """
        return frozenset(flag.value for flag in cls)


class Exit(IntEnum):
    """the process status codes the brain tools return.

    every tool means the same thing by a code. a check that reaches a verdict
    exits OK or FINDINGS; one that cannot reach a verdict - its input missing,
    git or a scan erroring - exits FAILED, so a caller never reads "could not
    look" as "looked and found nothing" or as "looked and found something"
    """

    # ran to a verdict, and there is nothing to report
    OK = 0
    # could not reach a verdict: the input is missing, or git or a scan could not run
    FAILED = 1
    # the command line was wrong
    USAGE = 2
    # b-sync: a merge stopped on conflicting files (`b-sync -h` lists every stop)
    CONFLICT = 3
    # ran to a verdict, and listed what fails it: a row, a crossing, a hit, a stale artifact, a failed check
    FINDINGS = 4
    # b-sync: any other stop it puts to him (`b-sync -h` lists every stop)
    BLOCKED = 5
