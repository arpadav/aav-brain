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
- the card vocabulary: Kind (rank + neo4j label) and Confidence
- the process surface: Env (every environment variable read), Flag (every
  command-line flag accepted), Args (one argv parse), Exit (every status code)
- the layouts: Layout and DataLayout, the ONE place a path inside the brain is
  spelled. every directory and file name appears exactly once, as a property
- the knowledge datatypes: Node, Edge
- the execution datatypes: State, Transition
- the build harness: Artifact (build / --check / drift-gate), reused by every
  builder so the "committed artifact must equal a fresh build" invariant lives
  in exactly one place
- the append-merge ledger: Ledger + MergeCount, the ONE reader and writer for
  every jsonl corpus (evidence and trace alike), so "a log may only ever grow"
  lives in one place too

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
import sys
from collections.abc import Iterable, Sequence
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
    REJECT = "--reject"
    SESSION = "--session"
    SINCE = "--since"
    SKILL = "--skill"
    SKILLS = "--skills"
    STALE = "--stale"
    STATE = "--state"
    SUPERSEDES = "--supersedes"
    TELLS = "--tells"


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

    def has(self, flag: Flag) -> bool:
        """whether a flag is present.

        # Arguments

        * `flag` - the flag to look for

        # Returns

        true when the flag appears anywhere in the arguments
        """
        return flag.value in self.tokens

    def value(self, flag: Flag, default: str = "") -> str:
        """the value following a flag, or a default.

        # Arguments

        * `flag` - the flag whose value to read
        * `default` - returned when the flag is absent or trails the arguments

        # Returns

        the token after the flag's first occurrence

        # Example

            >>> Args(("--state", "IMPL")).value(Flag.STATE)
            'IMPL'
            >>> Args(("--state",)).value(Flag.STATE, "?")
            '?'
        """
        for index, token in enumerate(self.tokens):
            if token == flag.value and index + 1 < len(self.tokens):
                return self.tokens[index + 1]
        return default

    def values(self, flag: Flag) -> list[str]:
        """every value following each occurrence of a repeatable flag.

        # Arguments

        * `flag` - the repeatable flag

        # Returns

        one value per occurrence, in argument order

        # Example

            >>> Args(("--principle", "P26", "--principle", "P28")).values(Flag.PRINCIPLE)
            ['P26', 'P28']
        """
        return [self.tokens[i + 1] for i, t in enumerate(self.tokens)
                if t == flag.value and i + 1 < len(self.tokens)]

    def positional(self, *taking: Flag) -> list[str]:
        """the arguments that are neither a flag nor a flag's value.

        # Arguments

        * `taking` - the flags of this tool that consume a following value, so
          those values are not mistaken for positional arguments

        # Returns

        the positional arguments, in order

        # Example

            >>> Args(("--since", "HEAD", "a.py", "b.py")).positional(Flag.SINCE)
            ['a.py', 'b.py']
        """
        consuming = {flag.value for flag in taking}
        rest: list[str] = []
        skip = False
        for token in self.tokens:
            if skip:
                skip = False
            elif token in consuming:
                skip = True
            elif not token.startswith("-"):
                rest.append(token)
        return rest

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
        return [t for t in self.tokens if t.startswith("--") and t not in allowed]


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
    """write a text file in the repo's encoding, creating its parents.

    # Arguments

    * `path` - the file to write
    * `content` - the text to write
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=ENCODING)


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

    type: str
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
        return cls(type=data["type"], src=data["src"], dst=data["dst"])


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
    """

    path: Path

    # bookkeeping the ledger itself stamps, excluded from a record's identity
    META: tuple[str, ...] = ("first_seen",)

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

    def write(self, rows: Iterable[dict[str, Any]]) -> Path:
        """overwrite the corpus with `rows`, one json object per line.

        for DERIVED files only - a projection whose every row is recomputed from
        a canonical corpus. anything append-only must go through merge/append

        # Arguments
        * `rows` - the records to write

        # Returns
        the path written to
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_text(self.path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        return self.path


@dataclass
class Decision:
    """one logged decision: what was chosen, what was rejected, what it affects.

    the decided-against entries are the point: a later session that disagrees
    reads `affects` to find exactly where the call was made and reverses it. when
    a call overturns a past one, `supersedes` carries the prior entry's ts so the
    reversal is machine-readable, not buried in the `decision` prose
    """

    skill: str
    decision: str
    chosen: str
    against: list[dict[str, str]] = field(default_factory=list)
    affects: str = ""
    principle: list[str] = field(default_factory=list)
    confidence: str = "medium"
    supersedes: str = ""


def trace_decision(decision: "Decision", session: str = "", ts: str = "") -> Path:
    """append one Decision to the trace (find_data()/trace/decisions.jsonl, OUTSIDE the repo; never overwrite).

    # Arguments
    * `decision` - a Decision instance
    * `session` - the current session id, for transcript correlation
    * `ts` - an iso utc timestamp; if empty, stamped now

    # Returns
    the resolved path the entry was appended to
    """
    entry = {"ts": ts or iso_now(), "session": session, **vars(decision)}
    return Ledger(find_data() / "trace" / "decisions.jsonl").append(entry)
