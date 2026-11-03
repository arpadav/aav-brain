"""brainlib.model: the datatypes one tool writes and another reads.

a Node read from a principle is the same Node recall ranks and b-graph exports,
and a State rendered by b-flow is the same State stepped by b-walk. that
shared shape is the whole point of the library

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.text import parse_frontmatter, read_text, write_text
from brainlib.tool import Args
from brainlib.vocab import Exit, Flag, Frontmatter, Kind, Rel, Tier

# --------------------------------------------------
# external
# --------------------------------------------------
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --------------------------------------------------
# constants
# --------------------------------------------------
# a [[link]] to a principle anywhere in a principle's file, frontmatter included;
# the captured id is a relates edge's destination
PRINCIPLE_LINK = re.compile(r"\[\[(principle-[a-z0-9-]+)\]\]")

@dataclass
class Node:
    """one principle as a graph node, read from its file by `from_principle`."""

    id: str
    kind: str
    headline: str
    interest: list[str]
    confidence: str
    tells: list[str]
    tension: list[str]
    body_links: list[str]
    path: str
    # contexts this principle loads in regardless of score; see schema/principle.md
    binds: list[str] = field(default_factory=list)
    # how this principle reaches an agent - always, by score, or on a lower bar (Tier)
    tier: str = Tier.CONDITIONAL

    def to_dict(self) -> Frontmatter:
        """serialise to the committed node shape (tension stays edge-only).

        # Returns
        an ordered dict with the human-meaningful field order

        # Example

            >>> principle = Node("principle-99-example", Kind.PRINCIPLE, "h", [], "c", [], [], [], "p")
            >>> list(principle.to_dict())[:3], "tension" in principle.to_dict()
            (['id', 'kind', 'tier'], False)
        """
        return {"id": self.id, "kind": self.kind, "tier": self.tier, "headline": self.headline,
                "interest": self.interest, "confidence": self.confidence, "binds": self.binds,
                "tells": self.tells, "body_links": self.body_links, "path": self.path}

    @property
    def short_id(self) -> str | None:
        """a principle's short id, the `P<nn>` that principles cite and `RecallIndex.resolve` reads back.

        # Returns

        `P` and the principle's number, or None for a node that is not a numbered principle

        # Example

            >>> principle = Node("principle-99-example", Kind.PRINCIPLE, "", [], "", [], [], [], "")
            >>> principle.short_id, Node("intent-craft", Kind.INTEREST, "", [], "", [], [], [], "").short_id
            ('P99', None)
        """
        number = self.id.removeprefix(f"{Kind.PRINCIPLE}-").split("-")[0]
        return f"P{number}" if self.kind == Kind.PRINCIPLE and number.isdigit() else None

    @classmethod
    def from_principle(cls, path: Path, kind: str, root: Path) -> "Node":
        """one principle file as a node.

        # Arguments

        * `path` - the principle file
        * `kind` - the kind its directory holds
        * `root` - the brain root `path` sits under; the node stores its path relative to it

        # Returns

        the node; a field the principle leaves out takes its default, and the id falls
        back to the file's stem
        """
        text = read_text(path)
        front = parse_frontmatter(text)
        return cls(id=cls._text(front, "name", path.stem), kind=kind,
                   headline=cls._text(front, "rule") or cls._text(front, "one_line") or path.stem,
                   interest=cls._list(front, "interest"), confidence=cls._text(front, "confidence"),
                   tells=cls._list(front, "tells"), tension=cls._list(front, "tension"),
                   body_links=sorted(set(PRINCIPLE_LINK.findall(text))), path=str(path.relative_to(root)),
                   binds=cls._list(front, "binds"), tier=cls._text(front, "tier") or Tier.CONDITIONAL)

    @staticmethod
    def _text(front: Frontmatter, key: str, default: str = "") -> str:
        """one frontmatter field as a string.

        parse_frontmatter types every value as scalar-or-list, so a field that must
        be a string is read through here rather than trusted

        # Arguments

        * `front` - the parsed frontmatter
        * `key` - the field name
        * `default` - returned when the field is absent or the wrong shape

        # Returns

        the string value, or the default

        # Example

            >>> Node._text({"name": "principle-01"}, "name"), Node._text({"tells": ["a", "b"]}, "tells", "?")
            ('principle-01', '?')
        """
        value = front.get(key, default)
        return value if isinstance(value, str) else default

    @staticmethod
    def _list(front: Frontmatter, key: str) -> list[str]:
        """one frontmatter field as a list of strings.

        # Arguments

        * `front` - the parsed frontmatter
        * `key` - the field name

        # Returns

        the list value, or an empty list when the field is absent or a scalar

        # Example

            >>> Node._list({"tells": ["never guess", "ask first"]}, "tells"), Node._list({"name": "p"}, "name")
            (['never guess', 'ask first'], [])
        """
        value = front.get(key, [])
        return value if isinstance(value, list) else []


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

        # Example

            >>> Edge(Rel.RELATES, "principle-01-a", "principle-02-b").to_dict() == {
            ...     "src": "principle-01-a", "dst": "principle-02-b", "type": "relates"}
            True
        """
        return {"src": self.src, "dst": self.dst, "type": self.type}


@dataclass(frozen=True)
class State:
    """one execution state, authored in flow.toml.

    `recall` is the single coupling to the graph: when true, the walker prints
    the b-recall call the agent runs to load context before the owner runs. `terminal` marks an end
    state with no exit. `regime` is the autonomy an entry state establishes
    (ask-first | execute-through), read from the entry, NOT inferred from the
    SANCTION crossing - review and self-refine reach a terminal without it
    """

    id: str
    kind: str
    owner: str
    recall: bool
    doc: str
    terminal: bool = False
    regime: str = ""
    # context tags this state's recall must bind, so the principles a scored query
    # would rank off the bottom still reach the owner
    binds: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "State":
        """reconstruct a State from a flow.toml `[[states]]` table.

        # Arguments
        * `data` - a state mapping; optional keys default

        # Returns
        a State

        # Example

            >>> State.from_dict({"id": "S", "kind": "work", "owner": "o", "recall": True, "doc": "d"}).terminal
            False
        """
        return cls(id=data["id"], kind=data["kind"], owner=data["owner"], recall=data["recall"],
                   doc=data["doc"], terminal=data.get("terminal", False),
                   regime=data.get("regime", ""),
                   binds=list(data.get("binds", [])))

    @property
    def owners(self) -> list[str]:
        """the bare owner names: an `a+b` composite split, each `:lens` suffix dropped.

        # Returns

        the names in authored order; a blank part yields an empty name

        # Example

            >>> State("S", "gate", "brain-meta-style:plan + worker", recall=False, doc="").owners
            ['brain-meta-style', 'worker']
        """
        return [part.split(":")[0].strip() for part in self.owner.split("+")]


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transition":
        """reconstruct a Transition from a flow.toml `[[transitions]]` table.

        # Arguments
        * `data` - a transition mapping; optional keys default

        # Returns
        a Transition

        # Example

            >>> Transition.from_dict({"src": "A", "on": "ok", "dst": "B"})
            Transition(src='A', on='ok', dst='B', guard='', boundary=False)
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

        # Example

            >>> import tempfile
            >>> class One(Artifact):
            ...     def targets(self): return [(self.out_dir / "one.txt", "1")]
            ...     def summary(self): return "one"
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     built = One(Path(tmp) / "out")
            ...     before = built.is_current()
            ...     built.emit()
            ...     before, built.is_current()
            one
            (False, True)
        """
        return all(path.exists() and read_text(path) == content for path, content in self.targets())

    def emit(self) -> None:
        """write every target and print this builder's summary.

        creates the output folder when it is missing, writes each
        `(path, content)` pair `targets` yields, then prints `summary` on
        stdout
        """
        self.out_dir.mkdir(parents=True, exist_ok=True)
        for path, content in self.targets():
            write_text(path, content)
        print(self.summary())

    def run(self, args: Args, label: str) -> Exit:
        """the build / --check harness for a single builder.

        # Arguments

        * `args` - the parsed command line
        * `label` - the tool's command (`Layout.command`), for messages and the rerun it names

        # Returns

        the verdict, as `run_all` gives it
        """
        return self.run_all([self], args, label)

    @staticmethod
    def run_all(artifacts: Sequence["Artifact"], args: Args, label: str) -> Exit:
        """the build / --check harness shared by every builder.

        --check names EVERY stale builder before exiting, so one drifting
        artifact cannot mask another behind an early exit

        # Arguments

        * `artifacts` - the Artifact instances to build or check
        * `args` - the parsed command line
        * `label` - the tool's command (`Layout.command`), for messages and the rerun it names

        # Returns

        FINDINGS when --check finds a stale builder, else OK
        """
        # --------------------------------------------------
        # check mode: name every stale builder, write nothing
        # --------------------------------------------------
        if args.has(Flag.CHECK):
            stale = [a for a in artifacts if not a.is_current()]
            if not stale:
                print(f"{label}: current")
                return Exit.OK
            for artifact in stale:
                print(f"{label}: DRIFT in {type(artifact).__name__} -> {artifact.out_dir}")
            print(f"{label}: re-run `{label}`")
            return Exit.FINDINGS
        # --------------------------------------------------
        # build mode
        # --------------------------------------------------
        for artifact in artifacts:
            artifact.emit()
        return Exit.OK
