#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brainlib: shared datatypes and helpers for the brain tools.

every brain script that needs one - cards, compile, extract, find, flow, graph,
recall, trace, walk - imports its datatypes and its drift-gate from here rather
than redefining them. a datatype written by one tool is the same datatype read
by another (graph writes Node.to_dict, recall reads Node.from_dict). that is the
library: scripts helping one another by sharing structs, not duplicating them

contents:
- pure helpers: clip, parse_frontmatter, iso_now, read_text, write_text
- the card vocabulary: Kind (rank + neo4j label), Rel (the closed edge vocabulary,
  with its neo4j label) and Confidence
- the process surface: Env (every environment variable read), Flag (every
  command-line flag accepted), Args (one argv parse), Exit (every status code),
  Mode (which region of the flow a walk traverses, and what a guard admits),
  Entry (every skill a walk can start from)
- the layouts: Layout and DataLayout, the ONE place a path inside the brain is
  spelled. every directory and file name appears exactly once, as a property
- the knowledge datatypes: Node, Edge
- the execution datatypes: State, Transition
- the build harness: Artifact (build / --check / drift-gate), reused by every
  builder so the "committed artifact must equal a fresh build" invariant lives
  in exactly one place
- the append-merge ledger: Ledger + MergeCount, the ONE reader and writer for
  every jsonl corpus (evidence and trace alike), so "a log may only ever grow"
  lives in one place too; `mark` layers a stale/pinned flag over that, which
  hides a record from readers without deleting it
- the decision trace: Decision (one logged fork, and how it appends itself) and
  PrunePolicy (how old an entry must be before it is even eligible to be judged
  stale, scaled by how fast the repo is moving)

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any

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

# how long a `git log` measurement may run before the answer is not worth waiting
# for; the caller falls back to the conservative window rather than hanging
GIT_TIMEOUT = 10

# a card's yaml header: scalars and lists, keyed by field name. the shape is
# what `parse_frontmatter` returns and what every card reader consumes
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


def clip(text: str, limit: int) -> str:
    r"""collapse whitespace and truncate text for storage.

    # Arguments
    * `text` - the raw text
    * `limit` - the maximum number of characters to keep

    # Returns
    the whitespace-collapsed, length-capped text

    # Example

        >>> clip("  a   ragged\n  line  ", 20)
        'a ragged line'
        >>> clip("truncated hard", 9)
        'truncated'
    """
    return re.sub(r"\s+", " ", text).strip()[:limit]


def iso_now() -> str:
    """the current instant as an iso-8601 utc stamp with microsecond resolution.

    the resolution is load-bearing: a record's ts is part of its identity, and
    `supersedes` keys on it, so two records in one second must not collide

    # Returns
    the stamp, e.g. `2026-08-17T13:24:41.290526Z`
    """
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def kind_rank(kind: str) -> int:
    """a card kind's sort position, tolerating an unknown kind.

    # Arguments

    * `kind` - the kind string as read from a card or the built graph

    # Returns

    the kind's rank, or one past the last known kind when unrecognised

    # Example

        >>> kind_rank("principle"), kind_rank("interest"), kind_rank("bogus")
        (0, 1, 2)
    """
    try:
        return Kind(kind).rank
    except ValueError:
        return len(Kind)


def read_text(path: Path) -> str:
    """read a text file in the repo's encoding.

    # Arguments

    * `path` - the file to read

    # Returns

    the file's decoded contents
    """
    return path.read_text(encoding=ENCODING)


def write_text(path: Path, content: str) -> None:
    """write a text file in the repo's encoding, atomically, creating its parents.

    the write lands on a temporary file in the same directory and is renamed
    over the target, so a reader sees either the whole previous file or the
    whole new one. a direct write truncates first, and a failure between the
    truncate and the last byte leaves a corpus that cannot be recovered - the
    ledger's rewriting paths carry records whose sources have expired

    # Arguments

    * `path` - the file to write
    * `content` - the text to write
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(f"{path.name}.tmp{os.getpid()}")
    try:
        staged.write_text(content, encoding=ENCODING)
        staged.replace(path)
    finally:
        staged.unlink(missing_ok=True)


def parse_frontmatter(text: str) -> Frontmatter:
    """parse a card's yaml-ish frontmatter without a yaml dependency.

    handles scalars, bare lists ([a, b]) for interest/tension, and quoted
    lists (["a, b"]) for tells

    # Arguments
    * `text` - the full card file contents

    # Returns
    a dict of frontmatter fields, or an empty dict if there is none
    """
    # --------------------------------------------------
    # isolate the block between the leading --- fences
    # --------------------------------------------------
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fields: Frontmatter = {}
    # --------------------------------------------------
    # parse one key: value per line
    # --------------------------------------------------
    for line in text[3:end].split("\n"):
        match = re.match(r"^([a-z_]+):\s*(.*)$", line.strip())
        if not match:
            continue
        key, rest = match.group(1), match.group(2).strip()
        if key == "tells":
            fields[key] = re.findall(r'"([^"]*)"', rest)
        elif rest.startswith("["):
            fields[key] = [t.strip() for t in rest.strip("[]").split(",") if t.strip()]
        else:
            fields[key] = rest
    return fields


@dataclass
class Node:
    """one card as a graph node. written by brain-graph, read by brain-recall."""

    id: str
    kind: str
    headline: str
    interest: list[str]
    confidence: str
    tells: list[str]
    tension: list[str]
    body_links: list[str]
    path: str
    # contexts this card loads in regardless of score; see schema/principle-card.md
    binds: list[str] = field(default_factory=list)

    def to_dict(self) -> Frontmatter:
        """serialise to the committed node shape (tension stays edge-only).

        # Returns
        an ordered dict with the human-meaningful field order
        """
        return {"id": self.id, "kind": self.kind, "headline": self.headline, "interest": self.interest,
                "confidence": self.confidence, "binds": self.binds, "tells": self.tells,
                "body_links": self.body_links, "path": self.path}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Node":
        """reconstruct a Node from a committed graph.json entry.

        # Arguments
        * `data` - a node dict from graph.json (no tension field)

        # Returns
        a Node with tension defaulted to empty
        """
        return cls(id=data["id"], kind=data["kind"], headline=data["headline"], interest=data["interest"],
                   confidence=data["confidence"], tells=data["tells"], tension=[],
                   body_links=data["body_links"], path=data["path"], binds=data.get("binds", []))


@dataclass(frozen=True, order=True)
class Edge:
    """one derived relationship. field order (type, src, dst) IS the sort order."""

    type: Rel
    src: str
    dst: str

    def to_dict(self) -> dict[str, str]:
        """serialise to the committed edge shape.

        # Returns
        a dict with keys src, dst, type
        """
        return {"src": self.src, "dst": self.dst, "type": self.type}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Edge":
        """reconstruct an Edge from a committed graph.json entry.

        # Arguments
        * `data` - an edge dict from graph.json

        # Returns
        an Edge
        """
        return cls(type=Rel(data["type"]), src=data["src"], dst=data["dst"])


@dataclass(frozen=True)
class State:
    """one execution state. written by brain-flow, read by brain-walk.

    `recall` is the single coupling to the graph: when true, the walker fires
    brain-recall to load context before the owner runs. `terminal` marks an end
    state with no exit. `entry` marks a multi-entry start node (an entry skill
    seeds the walker here); `regime` is the autonomy that entry establishes
    (ask-first | execute-through), read from the entry, NOT inferred from the
    SANCTION crossing - review and self-refine reach a terminal without it
    """

    id: str
    kind: str
    owner: str
    recall: bool
    doc: str
    terminal: bool = False
    entry: bool = False
    regime: str = ""
    # context tags this state's recall must bind, so the cards a scored query
    # would rank off the bottom still reach the owner
    binds: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, str | bool | list[str]]:
        """serialise to the committed state shape.

        # Returns
        an ordered dict with the state's fields
        """
        return {"id": self.id, "kind": self.kind, "owner": self.owner, "recall": self.recall,
                "terminal": self.terminal, "entry": self.entry, "regime": self.regime,
                "binds": self.binds, "doc": self.doc}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "State":
        """reconstruct a State from a committed flow.json or a flow.toml table.

        # Arguments
        * `data` - a state mapping; optional keys default

        # Returns
        a State
        """
        return cls(id=data["id"], kind=data["kind"], owner=data["owner"], recall=data["recall"],
                   doc=data["doc"], terminal=data.get("terminal", False),
                   entry=data.get("entry", False), regime=data.get("regime", ""),
                   binds=list(data.get("binds", [])))


@dataclass(frozen=True)
class Transition:
    """one guarded edge: from `src`, on outcome `on`, go to `dst`.

    `boundary` marks the single sanction transition that flips the regime
    """

    src: str
    on: str
    dst: str
    guard: str = ""
    boundary: bool = False

    def to_dict(self) -> dict[str, str | bool]:
        """serialise to the committed transition shape.

        # Returns
        a dict with keys src, dst, on, guard, boundary
        """
        return {"src": self.src, "dst": self.dst, "on": self.on, "guard": self.guard, "boundary": self.boundary}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transition":
        """reconstruct a Transition from flow.json or a flow.toml table.

        # Arguments
        * `data` - a transition mapping; optional keys default

        # Returns
        a Transition
        """
        return cls(src=data["src"], on=data["on"], dst=data["dst"],
                   guard=data.get("guard", ""), boundary=data.get("boundary", False))


@dataclass
class Artifact:
    """base for a built, committed, drift-checked artifact.

    a builder subclass implements `targets()` (the files it owns, as
    (path, content) pairs) and `summary()` (a one-line status). this base
    provides the byte-identical drift check and the build/--check harness, so
    that invariant - committed output must equal a fresh build - lives once
    """

    out_dir: Path

    def targets(self) -> list[tuple[Path, str]]:
        """the artifact files this builder owns.

        # Returns
        a list of (path, content-string) pairs. subclass responsibility
        """
        raise NotImplementedError

    def summary(self) -> str:
        """a one-line build summary.

        # Returns
        a status string. subclass responsibility
        """
        raise NotImplementedError

    def is_current(self) -> bool:
        """check whether every committed target matches a fresh build.

        # Returns
        true if all targets are byte-identical on disk
        """
        return all(path.exists() and read_text(path) == content for path, content in self.targets())

    def emit(self) -> None:
        """write every target and print this builder's summary."""
        self.out_dir.mkdir(parents=True, exist_ok=True)
        for path, content in self.targets():
            write_text(path, content)
        print(self.summary())

    def run(self, args: Args, label: str) -> None:
        """the build / --check harness for a single builder.

        # Arguments

        * `args` - the parsed command line
        * `label` - the tool name, for messages
        """
        self.run_all([self], args, label)

    @staticmethod
    def run_all(artifacts: Sequence["Artifact"], args: Args, label: str) -> None:
        """the build / --check harness shared by every builder.

        --check names EVERY stale builder before exiting, so one drifting
        artifact cannot mask another behind an early exit

        # Arguments

        * `artifacts` - the Artifact instances to build or check
        * `args` - the parsed command line
        * `label` - the tool name, for messages
        """
        # --------------------------------------------------
        # check mode: name every stale builder, write nothing
        # --------------------------------------------------
        if args.has(Flag.CHECK):
            stale = [a for a in artifacts if not a.is_current()]
            if not stale:
                print(f"{label}: artifacts are current")
                sys.exit(Exit.OK)
            for artifact in stale:
                print(f"{label}: DRIFT in {type(artifact).__name__} -> {artifact.out_dir}")
            print(f"{label}: re-run `python3 {label}.py`")
            sys.exit(Exit.DRIFT)
        # --------------------------------------------------
        # build mode
        # --------------------------------------------------
        for artifact in artifacts:
            artifact.emit()


def load_json(path: Path, label: str) -> Any:  # noqa: ANN401 - json.loads IS Any; the caller knows its artifact's shape
    """read a committed json artifact, exiting with a hint if it is missing.

    # Arguments
    * `path` - the json file path
    * `label` - the tool that should have built it, for the hint

    # Returns
    the parsed json
    """
    if not path.exists():
        sys.exit(f"no {path.name} - run `python3 {label}.py` first")
    return json.loads(read_text(path))


@dataclass(frozen=True)
class Layout:
    """every path inside the brain repo, derived from the discovered root.

    a directory name re-spelled at each call site is a rename that has to be
    found by grep and is silently wrong wherever the grep missed. here each
    name appears exactly once, so a move is one edit and every tool follows

    # Example

        layout = Layout.discover()
        cards = layout.principles.glob("*.md")
    """

    root: Path

    @classmethod
    def discover(cls) -> "Layout":
        """the layout rooted at the discovered brain.

        # Returns

        a Layout over `find_brain()`
        """
        return cls(find_brain())

    @property
    def bin(self) -> Path:
        """the tool directory.

        # Returns

        `<root>/bin`
        """
        return self.root / "bin"

    @property
    def agentic(self) -> Path:
        """the agent and skill tree.

        # Returns

        `<root>/agentic-files`
        """
        return self.root / "agentic-files"

    @property
    def agents(self) -> Path:
        """the agent definitions.

        # Returns

        `<root>/agentic-files/agents`
        """
        return self.agentic / "agents"

    @property
    def skills(self) -> Path:
        """the skill definitions.

        # Returns

        `<root>/agentic-files/skills`
        """
        return self.agentic / "skills"

    @property
    def store(self) -> Path:
        """the card store: the knowledge itself.

        # Returns

        `<root>/brain`
        """
        return self.root / "brain"

    @property
    def principles(self) -> Path:
        """the principle cards.

        # Returns

        `<root>/brain/principles`
        """
        return self.store / "principles"

    @property
    def intents(self) -> Path:
        """the intent cards.

        # Returns

        `<root>/brain/intents`
        """
        return self.store / "intents"

    @property
    def card_dirs(self) -> tuple[Path, Path]:
        """the two directories a card may live in.

        # Returns

        `(principles, intents)`, the order the graph and the linter walk them
        """
        return (self.principles, self.intents)

    @property
    def index(self) -> Path:
        """the card index loaded at session start.

        # Returns

        `<root>/brain/INDEX.md`
        """
        return self.store / "INDEX.md"

    @property
    def constitution(self) -> Path:
        """the file whose presence identifies a brain root.

        # Returns

        `<root>/brain/CONSTITUTION.md`
        """
        return self.store / "CONSTITUTION.md"

    @property
    def flow_dir(self) -> Path:
        """the flow source and its build output.

        # Returns

        `<root>/brain/flow`
        """
        return self.store / "flow"

    @property
    def flow_toml(self) -> Path:
        """the hand-edited flow source.

        # Returns

        `<root>/brain/flow/flow.toml`
        """
        return self.flow_dir / "flow.toml"

    @property
    def flow_json(self) -> Path:
        """the built flow the engine walks.

        # Returns

        `<root>/brain/flow/flow.json`
        """
        return self.flow_dir / "flow.json"

    @property
    def graph_dir(self) -> Path:
        """the built knowledge graph.

        # Returns

        `<root>/brain/graph`
        """
        return self.store / "graph"

    @property
    def graph_json(self) -> Path:
        """the graph recall reads.

        # Returns

        `<root>/brain/graph/graph.json`
        """
        return self.graph_dir / "graph.json"

    @property
    def graph_cypher(self) -> Path:
        """the graph's cypher rendering.

        # Returns

        `<root>/brain/graph/graph.cypher`
        """
        return self.graph_dir / "graph.cypher"

    @property
    def docs(self) -> Path:
        """the human-facing generated documentation.

        # Returns

        `<root>/docs`
        """
        return self.root / "docs"

    @property
    def prune_toml(self) -> Path:
        """the authored prune policy.

        # Returns

        `<root>/prune.toml`
        """
        return self.root / "prune.toml"

    @property
    def generated(self) -> Path:
        """the compiled output tree, gitignored.

        # Returns

        `<root>/.generated`
        """
        return self.root / ".generated"

    @property
    def codex_agents(self) -> Path:
        """where compiled codex agents land.

        # Returns

        `<root>/.generated/codex/agents`
        """
        return self.generated / "codex" / "agents"


@dataclass(frozen=True)
class DataLayout:
    """every path inside the brain's private data dir.

    the same rule as Layout, for the half that is never committed to the public
    repo: the decision trace and the extracted evidence corpus

    # Example

        data = DataLayout.discover()
        rows = Ledger(data.decisions).read()
    """

    root: Path

    @classmethod
    def discover(cls) -> "DataLayout":
        """the layout rooted at the private data dir.

        # Returns

        a DataLayout over `find_data()`
        """
        return cls(find_data())

    @property
    def trace(self) -> Path:
        """the decision-trace directory.

        # Returns

        `<data>/trace`
        """
        return self.root / "trace"

    @property
    def decisions(self) -> Path:
        """the append-only decision ledger.

        # Returns

        `<data>/trace/decisions.jsonl`
        """
        return self.trace / "decisions.jsonl"

    @property
    def evidence(self) -> Path:
        """the extracted evidence corpus.

        # Returns

        `<data>/evidence`
        """
        return self.root / "evidence"

    @property
    def corpus_stats(self) -> Path:
        """the corpus summary re-stamped by every extract.

        # Returns

        `<data>/evidence/corpus-stats.json`
        """
        return self.evidence / "corpus-stats.json"


def find_brain() -> Path:
    """locate the aav-brain repo root, no env var, no hardcode.

    the brain is ONE repo: cards, scripts (`bin/`), and the agentic files
    (`agentic-files/{agents,skills}`) all live under a single root. discovery
    returns that root; everything else derives from it (`<root>/bin`,
    `<root>/agentic-files/agents`, `<root>/agentic-files/skills`)

    resolution order, first hit wins:
    1. this file's own location (brainlib lives in <root>/bin/) - authoritative
       when called from a brain script
    2. a known brain-skill symlink under ~/.agents, then ~/.claude: readlink
       resolves the home-manager -> nix-store -> live-repo chain
    there is NO hardcoded-path fallback: a guess at a conventional checkout path
    (P32) would resolve a STALE sibling checkout, so discovery fails loud instead

    # Returns
    the resolved aav-brain root Path; raises FileNotFoundError if it cannot be
    located (fail loud, never guess)
    """
    # --------------------------------------------------
    # self-location: brainlib.py is <root>/bin/brainlib.py
    # --------------------------------------------------
    here = Path(__file__).resolve().parent.parent
    if (here / "brain" / "CONSTITUTION.md").exists():
        return here
    # --------------------------------------------------
    # follow a known skill symlink: ~/.agents first, then ~/.claude. skills live
    # at <root>/agentic-files/skills/<skill>, so the root is three parents up from
    # the resolved skill dir (skill -> skills -> agentic-files -> root)
    # --------------------------------------------------
    for base in (Path.home() / ".agents", Path.home() / ".claude"):
        link = base / "skills" / "brain-plan"
        if link.exists():
            root = link.resolve().parents[2]
            if (root / "brain" / "CONSTITUTION.md").exists():
                return root
    raise FileNotFoundError("cannot locate aav-brain via __file__ or the ~/.agents / ~/.claude skill symlink")


def find_data() -> Path:
    """the brain's PRIVATE memory dir (trace + evidence).

    private data - the decision trace and the extracted evidence corpus - never
    lives in the public brain's git objects. it lands in the XDG data dir
    (`$XDG_DATA_HOME/aav-brain`, else `~/.local/share/aav-brain`), which home-manager
    symlinks to the `aav-brain-logs` submodule (gitlinked at `logs/`; its content
    lives in a SEPARATE private repo, never in the public brain's history). resolved
    with no brain-specific env var (XDG is the standard, not a bespoke anchor); a
    relative `$XDG_DATA_HOME` is ignored, per the XDG spec

    # Returns
    the aav-brain private-data root Path (created on demand by its writers)
    """
    return _xdg_data() / "aav-brain"


def find_repo(start: Path | None = None) -> str:
    """the NAME of the git repository a decision was made in.

    an `affects` path is relative to the repo the run happened in, so without
    the repo it cannot be resolved later - `plans/01-scaffold.md` reads as
    deleted from anywhere else, which is indistinguishable from stale. the NAME
    and not the path: a machine-absolute path in a committed log is the same
    portability violation anywhere else (P32)

    # Arguments

    * `start` - where to start walking up from; the cwd when omitted

    # Returns

    the repo directory's name, or an empty string outside a repository

    # Example

        >>> find_repo(Path("/"))
        ''
    """
    here = (start or Path.cwd()).resolve()
    for directory in (here, *here.parents):
        if (directory / ".git").exists():
            return directory.name
    return ""


def find_archive() -> Path:
    """the cold store for RAW transcripts, a SIBLING of find_data(), never inside it.

    find_data() resolves into the `aav-brain-logs` submodule. curated evidence is
    versioned knowledge and belongs there; raw transcripts are bulk cache
    (hundreds of MB, growing forever) and must stay out of that git history

    # Returns
    the archive root Path (created on demand by its writer)
    """
    return _xdg_data() / "aav-brain-archive"


def _xdg_data() -> Path:
    """the XDG data root, ignoring a relative $XDG_DATA_HOME per the spec.

    # Returns
    the resolved data-home Path
    """
    base = Path(os.environ.get("XDG_DATA_HOME", "")).expanduser()
    if not base.is_absolute():
        base = Path.home() / ".local" / "share"
    return base


@dataclass(frozen=True)
class MergeCount:
    """the outcome of one merge: how many rows landed, held, and remain."""

    added: int
    kept: int
    total: int


@dataclass(frozen=True)
class Ledger:
    """a jsonl corpus that may only ever grow, deduped by content id.

    owns "a record once captured is never dropped" the same way Artifact owns
    "committed output must equal a fresh build" - the invariant lives here, and
    every corpus (evidence views, the decision trace) writes through this type
    rather than hand-rolling its own reader and writer

    the sources these records come from expire, so a full rebuild would delete
    evidence that can no longer be re-derived from anywhere; merging on content
    makes a re-run purely additive

    forgetting is therefore a MARK, not a delete: `mark` stamps META fields that
    readers filter on, so a corpus can drop a record from view and still restore
    it by clearing the mark. that is the only sanctioned way to shrink a read
    """

    path: Path

    # fields the ledger owns rather than the record: `first_seen` is stamped by a
    # merge, `stale` and `pinned` by a mark. all three are excluded from identity
    # because a marked record is the SAME record - in the payload a mark would
    # dedup as a second row beside the unmarked one
    META: tuple[str, ...] = ("first_seen", "stale", "pinned")

    @staticmethod
    def record_id(record: dict[str, Any]) -> str:
        """the stable content hash identifying one record.

        empty fields are dropped before hashing so a record written before an
        optional field existed collapses onto the same record written after it
        was added but left blank

        # Arguments
        * `record` - a json-serialisable dict

        # Returns
        a 16-hex-char content id
        """
        payload = {k: v for k, v in record.items()
                   if k not in Ledger.META and v not in ("", None, [], {})}
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        # sha1 identifies content here, it does not protect it: the id is a
        # dedup key over rows this machine wrote (S324 reads it as a security hash)
        return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]  # noqa: S324

    def read(self) -> list[dict[str, Any]]:
        """read the corpus, skipping any line that does not parse.

        # Returns
        the parsed records, or an empty list if the file does not exist
        """
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in read_text(self.path).splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
        return rows

    def append(self, record: dict[str, Any]) -> Path:
        """append one record in O(1), without rewriting the file.

        # Arguments
        * `record` - a json-serialisable dict

        # Returns
        the path written to
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding=ENCODING) as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return self.path

    def merge(self, rows: Iterable[dict[str, Any]]) -> "MergeCount":
        """union `rows` into the corpus, deduped by content id. never truncates.

        # Arguments
        * `rows` - the records to merge in

        # Returns
        a MergeCount
        """
        # --------------------------------------------------
        # whatever is already on disk is authoritative and survives
        # --------------------------------------------------
        merged = {self.record_id(existing): existing for existing in self.read()}
        # --------------------------------------------------
        # union in the new rows; an id already present keeps its first_seen
        # --------------------------------------------------
        kept, added, stamp = len(merged), 0, iso_now()
        for row in rows:
            key = self.record_id(row)
            if key in merged:
                continue
            merged[key] = {**row, "first_seen": stamp}
            added += 1
        # --------------------------------------------------
        # deterministic order: chronological, id breaking ties for undated rows
        # --------------------------------------------------
        ordered = sorted(merged.items(), key=lambda kv: (str(kv[1].get("ts") or ""), kv[0]))
        self.write(row for _, row in ordered)
        return MergeCount(added, kept, len(merged))

    def mark(self, stamps: Mapping[str, Mapping[str, bool]]) -> int:
        """stamp bookkeeping fields on the records named by `ts`, keeping every row.

        this is how a corpus forgets without losing anything: a record marked
        `stale` is skipped by readers but stays on disk, so restoring it is
        clearing the mark rather than recovering it from somewhere. the fields
        are META, which is what keeps a mark out of the content id

        # Arguments

        * `stamps` - the fields to set, keyed by the `ts` of the record to set
          them on. a field set to false is removed rather than written as false,
          so an unmarked record stays byte-identical to one never marked

        # Returns

        the number of records stamped; a `ts` matching nothing is a no-op
        """
        # --------------------------------------------------
        # walk the RAW lines: a line this reader cannot parse is still a record,
        # and `read` skipping it must not become `write` dropping it
        # --------------------------------------------------
        touched = 0
        kept: list[str] = []
        for line in read_text(self.path).splitlines() if self.path.exists() else []:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                kept.append(line)
                continue
            fields = stamps.get(str(row.get("ts", "")))
            if not fields:
                kept.append(line)
                continue
            for name, value in fields.items():
                if value:
                    row[name] = True
                else:
                    row.pop(name, None)
            kept.append(json.dumps(row, ensure_ascii=False))
            touched += 1
        # --------------------------------------------------
        # rewrite only when a stamp actually landed
        # --------------------------------------------------
        if touched:
            write_text(self.path, "".join(f"{line}\n" for line in kept))
        return touched

    def write(self, rows: Iterable[dict[str, Any]]) -> Path:
        """overwrite the corpus with `rows`, one json object per line.

        for DERIVED files only - a projection whose every row is recomputed from
        a canonical corpus. anything append-only must go through merge/append,
        or `mark`, which rewrites the same rows it read and adds none

        # Arguments
        * `rows` - the records to write

        # Returns
        the path written to
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_text(self.path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        return self.path


@dataclass(frozen=True)
class PrunePolicy:
    """how old a trace entry must be before it is ELIGIBLE to be judged.

    eligibility is an age filter and nothing more. it narrows a several-hundred
    entry trace to the ones worth reading; deciding that any particular one is
    actually stale is a judgement made against what the brain is now, entry by
    entry. a tool that pruned everything past the cutoff would delete the oldest
    and most load-bearing decisions in the store first

    the window follows commit frequency because that is what sets how fast a
    decision goes out of date: a repo being reshaped weekly invalidates a
    three-week-old call, a quiet one does not

    # Example

        policy = PrunePolicy.load(LAYOUT.prune_toml)
        cutoff = policy.cutoff(rate=policy.commit_rate(LAYOUT.root))
    """

    busy_commits_per_week: float = 10.0
    sample_weeks: int = 8
    fast_days: int = 21
    slow_days: int = 60

    @classmethod
    def load(cls, path: Path) -> "PrunePolicy":
        """read the policy, falling back to the defaults when it is absent.

        # Arguments

        * `path` - the prune.toml path

        # Returns

        the policy; the field defaults when the file is absent, unreadable,
        malformed or the wrong shape. a broken config must WIDEN the window to
        the conservative default, never stop the tool - the same file is read
        beside the path that records decisions
        """
        if not path.is_file():
            return cls()
        try:
            window = tomllib.loads(read_text(path)).get("window", {})
            return cls(
                busy_commits_per_week=float(window.get("busy_commits_per_week", cls.busy_commits_per_week)),
                sample_weeks=max(1, int(window.get("sample_weeks", cls.sample_weeks))),
                fast_days=max(1, int(window.get("fast_days", cls.fast_days))),
                slow_days=max(1, int(window.get("slow_days", cls.slow_days))),
            )
        except (tomllib.TOMLDecodeError, AttributeError, TypeError, ValueError, OSError) as broken:
            print(f"prune policy unreadable ({broken}); using defaults", file=sys.stderr)
            return cls()

    def commit_rate(self, repo: Path) -> float:
        """commits per week in this repo over the sample window.

        # Arguments

        * `repo` - the repository to measure

        # Returns

        the rate; 0.0 when git is unavailable or the repo has no commits in the
        window, which selects the slow (more conservative) window
        """
        git = shutil.which("git")
        if git is None:
            return 0.0
        argv = [git, "-C", str(repo), "log", "--since", f"{self.sample_weeks} weeks ago", "--format=%H"]
        # GIT_DIR and GIT_WORK_TREE outrank -C, so an inherited environment would
        # silently measure a DIFFERENT repo than the one asked for
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        # argv is this method's own literals plus a discovered repo path; nothing
        # here is remote input, and shell=False keeps it an exec not a shell (S603)
        try:
            done = subprocess.run(argv, capture_output=True, text=True, check=False,  # noqa: S603
                                  env=env, timeout=GIT_TIMEOUT)
        except (OSError, subprocess.SubprocessError):
            return 0.0
        if done.returncode != 0:
            return 0.0
        return len(done.stdout.split()) / self.sample_weeks

    def window_days(self, rate: float) -> int:
        """the eligibility window for a given commit rate.

        # Arguments

        * `rate` - commits per week

        # Returns

        the short window when the repo is busy, the long one otherwise

        # Example

            >>> policy = PrunePolicy()
            >>> policy.window_days(25.0), policy.window_days(1.0)
            (21, 60)
        """
        return self.fast_days if rate >= self.busy_commits_per_week else self.slow_days

    def cutoff(self, rate: float, now: datetime.datetime | None = None) -> str:
        """the iso timestamp an entry must predate to be eligible.

        # Arguments

        * `rate` - commits per week, from `commit_rate`
        * `now` - the reference time; utc now when omitted

        # Returns

        an iso-8601 utc timestamp, string-comparable against a record's `ts`

        # Example

            >>> at = datetime.datetime(2026, 3, 1, tzinfo=datetime.UTC)
            >>> PrunePolicy().cutoff(1.0, at)
            '2025-12-31T00:00:00.000000Z'
        """
        moment = now or datetime.datetime.now(datetime.UTC)
        back = datetime.timedelta(days=self.window_days(rate))
        # microseconds, matching iso_now: a record and this cutoff are compared
        # as STRINGS, and at second precision `.` sorts below `Z`, so a record
        # stamped inside the cutoff second would read as older than it
        return (moment - back).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass
class Decision:
    """one logged decision: what was chosen, what was rejected, what it affects.

    the decided-against entries are the point: a later session that disagrees
    reads `affects` to find exactly where the call was made and reverses it. when
    a call overturns a past one, `supersedes` carries the prior entry's ts so the
    reversal is machine-readable, not buried in the `decision` prose. `repo`
    is what makes `affects` resolvable at all: the trace spans every repo the
    brain works in, and the same relative path means a different file in each
    """

    skill: str
    decision: str
    chosen: str
    against: list[dict[str, str]] = field(default_factory=list)
    affects: str = ""
    repo: str = ""
    principle: list[str] = field(default_factory=list)
    confidence: str = "medium"
    supersedes: str = ""

    def trace(self, ledger: "Ledger | None" = None, session: str = "", ts: str = "") -> Path:
        """append this decision to the trace; never overwrite.

        the ledger defaults to the discovered one rather than a path spelled
        here, because `DataLayout` owns where the trace lives and a second
        spelling is a second thing to keep in step

        # Arguments

        * `ledger` - the corpus to append to; the discovered trace when omitted
        * `session` - the current session id, for transcript correlation
        * `ts` - an iso utc timestamp; stamped now when empty

        # Returns

        the resolved path the entry was appended to
        """
        target = ledger if ledger is not None else Ledger(DataLayout.discover().decisions)
        entry = {"ts": ts or iso_now(), "session": session, **vars(self)}
        # an unset repo means "the repo this ran in", which only this type knows
        entry["repo"] = entry["repo"] or find_repo()
        return target.append(entry)
