"""brainlib.model: the datatypes one tool writes and another reads.

a Node written by brain-graph is the same Node read by brain-recall, and a
State written by brain-flow is the same State stepped by brain-walk. that
shared shape is the whole point of the library

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.args import Args
from brainlib.text import read_text, write_text
from brainlib.vocab import Exit, Flag, Frontmatter, Rel, Tier

# --------------------------------------------------
# external
# --------------------------------------------------
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    # how this card reaches an agent - always, by score, or on a lower bar (Tier)
    tier: str = Tier.CONDITIONAL

    def to_dict(self) -> Frontmatter:
        """serialise to the committed node shape (tension stays edge-only).

        # Returns
        an ordered dict with the human-meaningful field order
        """
        return {"id": self.id, "kind": self.kind, "tier": self.tier, "headline": self.headline,
                "interest": self.interest, "confidence": self.confidence, "binds": self.binds,
                "tells": self.tells, "body_links": self.body_links, "path": self.path}

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
                   body_links=data["body_links"], path=data["path"], binds=data.get("binds", []),
                   tier=data.get("tier", Tier.CONDITIONAL))


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
