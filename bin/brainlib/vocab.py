"""brainlib.vocab: the closed vocabularies every brain tool shares.

a name spelled at its call site is a literal the reader cannot grep for and
the type checker cannot see. every enum here exists so a rename is one edit
and the set a tool depends on is a list rather than an archaeology exercise

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import os
from enum import IntEnum, StrEnum
from pathlib import Path

# constants
# --------------------------------------------------
# every file this repo reads or writes is text in this encoding, so the argument
# is a property of the repo rather than of any one call site
ENCODING = "utf-8"

# the interpreter floor. the checkers are pinned to it here; the same number is
# declared to each tool in its own config (ruff target-version, ty python-version,
# mypy python_version, pyright pythonVersion) and to `uv run` by the script headers
PYTHON_VERSION = "3.12"

# how long a `git log` measurement may run before the answer is not worth waiting
# for; the caller falls back to the conservative window rather than hanging
GIT_TIMEOUT = 10

# a card's yaml header: scalars and lists, keyed by field name. the shape the
# parser in brainlib.text returns and every card reader consumes
type Frontmatter = dict[str, str | list[str]]


class Kind(StrEnum):
    """the two kinds of card, with the ordering derived from them.

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
    """how a card reaches an agent: always, by score, or by a lower bar.

    CONSTITUTION cards skip scoring and load on every recall, CONDITIONAL cards
    are scored, NARROW cards clear a lower bar. the split is measured, not
    asserted: tiers.toml holds the rule, its thresholds, the measurement and the
    caveats behind every assignment
    """

    CONSTITUTION = "constitution"
    CONDITIONAL = "conditional"
    NARROW = "narrow"


class Confidence(StrEnum):
    """how strong the evidence behind a card is, per schema/principle-card.md.

    # Example

        >>> Confidence("very-high")
        <Confidence.VERY_HIGH: 'very-high'>
    """

    VERY_HIGH = "very-high"
    HIGH = "high"
    MEDIUM = "medium"


class Env(StrEnum):
    """every environment variable the brain reads, named once.

    a variable name spelled at its call site is a literal the reader cannot
    grep for and the type checker cannot see. reading through the member means
    a rename is one edit, and the set of variables the brain depends on is a
    list rather than an archaeology exercise
    """

    AAV_BRAIN = "AAV_BRAIN"
    XDG_DATA_HOME = "XDG_DATA_HOME"
    XDG_CONFIG_HOME = "XDG_CONFIG_HOME"
    SESSION_ID = "CLAUDE_CODE_SESSION_ID"

    def read(self, default: str = "") -> str:
        """this variable's value, or a default when it is unset or empty.

        # Arguments

        * `default` - returned when the variable is unset or empty

        # Returns

        the variable's value

        # Example

            >>> import os
            >>> saved = os.environ.pop(Env.AAV_BRAIN, None)
            >>> Env.AAV_BRAIN.read("unset")
            'unset'
            >>> os.environ[Env.AAV_BRAIN] = "/srv/brain"
            >>> Env.AAV_BRAIN.read("unset")
            '/srv/brain'
            >>> _ = os.environ.pop(Env.AAV_BRAIN) if saved is None else os.environ.__setitem__(Env.AAV_BRAIN, saved)
        """
        return os.environ.get(self.value, "") or default

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
    """every command-line flag the brain tools accept, named once.

    a flag spelled as a literal at each site hides a typo in one comparison, and
    the set a tool accepts is recoverable only by grep. as members they are
    enumerable, which is what lets `Tool.admit` reject a misspelled flag
    instead of ignoring it
    """

    AFFECTS = "--affects"
    AGAINST = "--against"
    AGENTS = "--agents"
    ALL = "--all"
    ARCHIVE = "--archive"
    ARCHIVE_DIR = "--archive-dir"
    BIN = "--bin"
    BINDS = "--binds"
    CHECK = "--check"
    CHOSEN = "--chosen"
    DECISION = "--decision"
    EXPORT = "--export"
    GATE = "--gate"
    HELP = "--help"
    LAST = "--last"
    LIST = "--list"
    MERMAID = "--mermaid"
    MODE = "--mode"
    # the short flags: `-n` because recall is typed by hand, `-h` by convention
    N = "-n"
    HELP_SHORT = "-h"
    NEIGHBORS = "--neighbors"
    ON = "--on"
    OUT = "--out"
    PRINCIPLE = "--principle"
    PRUNE = "--prune"
    PRUNED = "--pruned"
    REJECT = "--reject"
    RESTORE = "--restore"
    RUN = "--run"
    SESSION = "--session"
    SINCE = "--since"
    SKILL = "--skill"
    SKILLS = "--skills"
    STAGING = "--staging"
    STALE = "--stale"
    STALE_CANDIDATES = "--stale-candidates"
    STATE = "--state"
    SUPERSEDES = "--supersedes"
    TAG = "--tag"
    TELLS = "--tells"

    @classmethod
    def valued(cls) -> frozenset["Flag"]:
        """every flag whose meaning is the token after it.

        knowing this globally is what lets `Args` tell a FLAG from a flag-shaped
        VALUE. without it `--decision "--prune vs --delete"` reads as a request
        to prune, and `--prune --restore TS` reads `--restore` as the timestamp
        to prune and pins the entry instead

        # Returns

        the value-taking flags; every other member is a bare switch

        # Example

            >>> Flag.DECISION in Flag.valued(), Flag.CHECK in Flag.valued()
            (True, False)
        """
        return frozenset({
            cls.AFFECTS, cls.ARCHIVE_DIR, cls.BINDS, cls.CHOSEN, cls.DECISION, cls.MODE, cls.N,
            cls.NEIGHBORS, cls.ON, cls.OUT, cls.PRINCIPLE, cls.PRUNE, cls.REJECT, cls.RESTORE,
            cls.SESSION, cls.SINCE, cls.SKILL, cls.STATE, cls.SUPERSEDES, cls.TAG,
        })


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
    # brain-sync: a merge stopped on conflicting files, left in progress to resolve
    CONFLICT = 3
    # ran to a verdict, and listed what fails it: a row, a crossing, a hit, a stale artifact, a failed check
    FINDINGS = 4
    # brain-sync: origin could not be fetched or kept refusing the push
    BLOCKED = 5
