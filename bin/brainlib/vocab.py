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
    """the two kinds of card, with the ordering and labels derived from them.

    the rank is the tie-break shared by the graph build and recall; the label is
    the neo4j node label. both used to be separate string-keyed tables that a
    third kind would have had to be added to in three places.
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

    @property
    def label(self) -> str:
        """this kind's neo4j node label.

        # Returns

        the capitalised label

        # Example

            >>> Kind.INTEREST.label
            'Interest'
        """
        return self.value.capitalize()


class Rel(StrEnum):
    """every derived relationship an edge can carry, named once.

    the graph's edge vocabulary is closed and derived - never authored - so it
    belongs here rather than in the builder that writes it and again in the
    reader that traverses it. the neo4j label comes off the member, the way
    Kind's does, instead of a parallel string-keyed table a fifth relationship
    would have to be added to twice

    # Example

        >>> Rel.SERVED_BY.label
        'SERVED_BY'
    """

    # no producer since intents stopped being nodes: brain-graph emits neither,
    # and brain-recall's reference set holds neither. kept because graph.json
    # files built before that change still carry them, and `Rel(edge["type"])`
    # must resolve rather than exit on an older artifact
    SERVES = "serves"
    SERVED_BY = "served_by"
    RELATES = "relates"
    TENSION = "tension"

    @property
    def label(self) -> str:
        """this relationship's neo4j label.

        # Returns

        the upper-cased label

        # Example

            >>> Rel.RELATES.label
            'RELATES'
        """
        return self.value.upper()


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
    LIST = "--list"
    LOW_CONFIDENCE = "--low-confidence"
    MERMAID = "--mermaid"
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
    EDIT = "--edit"
    SELF_REFINE = "--self-refine"
    SESSION = "--session"
    SINCE = "--since"
    SKILL = "--skill"
    SKILLS = "--skills"
    STALE = "--stale"
    STALE_CANDIDATES = "--stale-candidates"
    STATE = "--state"
    SUPERSEDES = "--supersedes"
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
            cls.CONFIG, cls.CONFIG_FILE, cls.DECISION, cls.N, cls.NEIGHBORS, cls.ON,
            cls.OUT, cls.PRINCIPLE, cls.PROJECT, cls.PRUNE, cls.REJECT, cls.RESTORE,
            cls.SESSION, cls.SINCE, cls.SKILL, cls.STATE, cls.SUPERSEDES, cls.TELLS,
        })


class Mode(StrEnum):
    """which region of the one flow a walk is traversing.

    a transition may carry a guard naming a mode, so the same (state, event)
    can lead somewhere different in a refine run than in a build. the mode is a
    DECLARED input to the walk, never ambient state - `brain-walk --state X
    --on E --self-refine` stays a pure function of its arguments (P30).
    """

    BUILD = "build"
    SELF_REFINE = "self_refine"
    EDIT = "edit"

    @classmethod
    def of(cls, *, self_refine: bool = False, edit: bool = False) -> "Mode":
        """the mode a walk is in.

        # Arguments

        * `self_refine` - true when the caller is brain-self-refine
        * `edit` - true when the caller is brain-edit

        # Returns

        the matching mode; BUILD when neither flag is present, which is what a
        plan or execute run gets. refine and edit are separate because they
        differ from a build in the same way (no phase list) but from each other
        in whether verification may be skipped

        # Example

            >>> Mode.of(self_refine=True), Mode.of(edit=True), Mode.of()
            (<Mode.SELF_REFINE: 'self_refine'>, <Mode.EDIT: 'edit'>, <Mode.BUILD: 'build'>)
        """
        if self_refine:
            return cls.SELF_REFINE
        return cls.EDIT if edit else cls.BUILD

    def satisfies(self, guard: str) -> bool:
        """whether a transition's guard admits this mode.

        an empty guard admits every mode; `self_refine` admits only that mode;
        `!self_refine` admits every other

        # Arguments

        * `guard` - the transition's guard string

        # Returns

        true when the guarded edge is available in this mode

        # Example

            >>> Mode.BUILD.satisfies(""), Mode.BUILD.satisfies("!self_refine")
            (True, True)
            >>> Mode.BUILD.satisfies("self_refine")
            False
            >>> Mode.SELF_REFINE.satisfies("self_refine")
            True
        """
        if not guard:
            return True
        negated = guard.startswith("!")
        return (guard.lstrip("!") == self.value) != negated


class Entry(StrEnum):
    """every skill the user types to START a walk, named once.

    an entry is the one skill in a run that is already in context before the
    engine moves: it is the caller. two tools need that set and must never
    disagree on it - brain-flow renders the drive handoff into each entry's
    SKILL.md, and brain-walk suppresses a load directive for each, since
    directing an entry to load itself is re-entry. a state's `owner` cannot
    stand in for the set: an entry state is owned by whatever does its WORK,
    which is nobody for IDEATION and brain-meta-author-prompt for DOCTRINE
    """

    PLAN = "brain-plan"
    EXECUTE = "brain-execute"
    EDIT = "brain-edit"
    REVIEW = "brain-review"
    SELF_REFINE = "brain-self-refine"


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
