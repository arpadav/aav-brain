"""brainlib.vocab: the closed vocabularies every brain tool shares.

a name spelled at its call site is a literal the reader cannot grep for and
the type checker cannot see. every enum here exists so a rename is one edit
and the set a tool depends on is a list rather than an archaeology exercise

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------

# --------------------------------------------------
# external
# --------------------------------------------------
import os
from enum import IntEnum, StrEnum

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

    # no producer since intents stopped being nodes: brain-graph emits neither,
    # and brain-recall's reference set holds neither. kept because graph.json
    # files built before that change still carry them, and `Rel(edge["type"])`
    # must resolve rather than exit on an older artifact
    SERVES = "serves"
    SERVED_BY = "served_by"
    RELATES = "relates"
    TENSION = "tension"


class Tier(StrEnum):
    """how a card reaches an agent: always, by score, or by a lower bar.

    measured, not asserted, and the measurement is in tiers.toml. two signals
    define the split - how often a card was judged relevant across a labelled
    prompt set, and how often the retriever surfaced it across the real corpus
    before this work. the interesting cases are where they DISAGREE: a card
    judged relevant on 28% of prompts and served on 1% of them is not a
    conditional card, it is a constitutional one the scorer does not find

    CONSTITUTION cards skip scoring entirely. that is not a shortcut - 39% of
    true relevance shares no content token with its card, so for those cards no
    amount of scoring reaches them and always-loading is strictly better

    NARROW is the opposite end: the lowest measured breadth in the store. a
    threshold tuned for breadth would never admit one, so they get a lower bar -
    a bet that a rare card is specific rather than dead. tiers.toml records the
    rule, its thresholds and the caveats behind every assignment
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


class Flag(StrEnum):
    """every command-line flag the brain tools accept, named once.

    the flags were previously bare string literals compared by hand at each
    site, so a typo in one comparison was invisible and the set a tool accepted
    could only be recovered by grep. as members they are enumerable, which is
    what lets `Args.unknown` reject a misspelled flag instead of ignoring it
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
    CONFIDENCE = "--confidence"
    CONFIG = "--config"
    CONFIG_FILE = "--config-file"
    DECISION = "--decision"
    EXPORT = "--export"
    GATE = "--gate"
    HELP = "--help"
    LAST = "--last"
    LIST = "--list"
    LOW_CONFIDENCE = "--low-confidence"
    MERMAID = "--mermaid"
    MODE = "--mode"
    # the one short flag the brain accepts, kept short because recall is typed by hand
    N = "-n"
    NEIGHBORS = "--neighbors"
    ON = "--on"
    OUT = "--out"
    PRINCIPLE = "--principle"
    PROJECT = "--project"
    PRUNE = "--prune"
    PRUNED = "--pruned"
    REJECT = "--reject"
    RESTORE = "--restore"
    SESSION = "--session"
    SINCE = "--since"
    SKILL = "--skill"
    SKILLS = "--skills"
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
            cls.AFFECTS, cls.ARCHIVE_DIR, cls.BINDS, cls.CHOSEN, cls.CONFIDENCE,
            cls.CONFIG, cls.CONFIG_FILE, cls.DECISION, cls.MODE, cls.N, cls.NEIGHBORS, cls.ON,
            cls.OUT, cls.PRINCIPLE, cls.PROJECT, cls.PRUNE, cls.REJECT, cls.RESTORE,
            cls.SESSION, cls.SINCE, cls.SKILL, cls.STATE, cls.SUPERSEDES, cls.TAG, cls.TELLS,
        })


class Exit(IntEnum):
    """the process status codes the brain tools return.

    every tool means the same thing by a code: OK is "nothing to report", DRIFT
    is "a committed artifact no longer matches a fresh build", and USAGE is "the
    command line was wrong". spelling them as 0/1/2 at nineteen call sites let
    the same integer mean three different things
    """

    OK = 0
    DRIFT = 1
    USAGE = 2
    # brain-sync: a merge stopped on conflicting files, left in progress to resolve
    CONFLICT = 3
