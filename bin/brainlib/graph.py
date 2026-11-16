"""brainlib.graph: the principles as a graph, built from the principles on every call.

nodes: one per principle, of kind `Kind.PRINCIPLE`, keyed by its `name:`
or else its file stem, a later duplicate replacing an earlier one. `Graph.build`
says why interests and voice docs are not nodes

edges: derived from the principles, never authored; `Rel` is the closed set
- `relates`: one per `[[principle-...]]` link anywhere in a principle's file, to the
  principle it names
- `tension`: one each way for every principle named in a principle's `tension:` field

warnings: a link or tension naming no principle, which gets no edge; a principle in
tension with itself; an orphan no edge touches

determinism: nodes in (kind, id) order, edges sorted by (type, src, dst),
warnings sorted and deduplicated, so `Graph.to_json` is byte-identical for the
same principles

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.enums import Frontmatter, Kind, Rel, Tier
from brainlib.file_io import kind_rank, parse_frontmatter, read_text
from brainlib.paths import Layout

# --------------------------------------------------
# external
# --------------------------------------------------
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

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
            >>> principle.short_id, Node("interest-craft", Kind.INTEREST, "", [], "", [], [], [], "").short_id
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
class Graph:
    r"""the principles as nodes and the links between them as edges, derived, never authored.

    # Example

        >>> import tempfile
        >>> from pathlib import Path
        >>> with tempfile.TemporaryDirectory() as folder:
        ...     layout = Layout(Path(folder))
        ...     layout.principles.mkdir(parents=True)
        ...     principle = "---\nname: principle-{}\ntension: [{}]\n---\n{}\n"
        ...     _ = (layout.principles / "a.md").write_text(principle.format("a", "principle-b", "[[principle-b]]"))
        ...     _ = (layout.principles / "b.md").write_text(principle.format("b", "", "[[principle-x]]"))
        ...     graph = Graph.build(layout)
        ...     _ = (layout.principles / "c.md").write_text(principle.format("b", "", ""))
        ...     Graph.build(layout).warnings[0]
        'principle-b is named by both store/principles/b.md and store/principles/c.md; store/principles/c.md is kept'
        >>> for edge in graph.edges:
        ...     print(edge.type, edge.src, edge.dst)
        relates principle-a principle-b
        tension principle-a principle-b
        tension principle-b principle-a
        >>> graph.warnings
        ['principle-b relates to unknown principle-x']
    """

    # in (kind, id) order: the order graph.json and recall both use
    nodes: dict[str, Node]
    # sorted by (type, src, dst)
    edges: list[Edge]
    # sorted, deduplicated
    warnings: list[str]

    @classmethod
    def build(cls, layout: Layout) -> "Graph":
        """read every principle in the layout's principles and derive the edges between them.

        store/interests/ is deliberately not read: an interest is the WHY of its
        principles and never fires independently, so as a peer node it could
        only ever co-occur with them. measured on a labelled prompt set,
        interest-comprehension and P11 were relevant on 86% of the same prompts
        while sharing 12% of their vocabulary - two nodes, one rule. five of the
        seven highest-overlap principle pairs in the store paired an interest with a
        principle. the interest files remain prose a human reads and valid
        [[link]] targets, and each principle's `interest:` field carries the
        association without a node to hang it on. voice docs are retrieved by
        name, not traversal, so they are not nodes either

        # Arguments

        * `layout` - the brain whose principles to read; a missing principles
          directory reads as no principles

        # Returns

        the graph, its warnings naming each duplicate name, unknown link, self-tension and orphan
        """
        # --------------------------------------------------
        # one node per principle, a later duplicate name replacing an earlier one
        # --------------------------------------------------
        read: dict[str, Node] = {}
        duplicates: list[str] = []
        for path in sorted(layout.principles.glob("*.md")):
            node = Node.from_principle(path, Kind.PRINCIPLE, layout.root)
            if (earlier := read.get(node.id)) is not None:
                duplicates.append(f"{node.id} is named by both {earlier.path} and {node.path}; {node.path} is kept")
            read[node.id] = node
        nodes = {node.id: node for node in sorted(read.values(), key=lambda n: (kind_rank(n.kind), n.id))}
        # --------------------------------------------------
        # each relationship kind is derived by its own pass
        # --------------------------------------------------
        relates, unlinked = cls._relates(nodes)
        tensions, untensed = cls._tensions(nodes)
        edges = relates | tensions
        warnings = [*duplicates, *unlinked, *untensed, *cls._orphans(nodes, edges)]
        return cls(nodes, sorted(edges), sorted(set(warnings)))

    @staticmethod
    def _relates(nodes: dict[str, Node]) -> tuple[set[Edge], list[str]]:
        """the relates edges, one per [[link]] in a principle's file.

        # Arguments

        * `nodes` - every principle, by id

        # Returns

        an (edges, warnings) tuple; a warning names a link with no principle, which
        gets no edge, so no reader has to guard a destination that is not there
        """
        edges: set[Edge] = set()
        warnings: list[str] = []
        for node in nodes.values():
            for other in node.body_links:
                if other == node.id:
                    continue
                if other not in nodes:
                    warnings.append(f"{node.id} relates to unknown {other}")
                    continue
                edges.add(Edge(Rel.RELATES, node.id, other))
        return edges, warnings

    @staticmethod
    def _tensions(nodes: dict[str, Node]) -> tuple[set[Edge], list[str]]:
        """the tension edges, symmetric, from each principle's `tension:` field.

        # Arguments

        * `nodes` - every principle, by id

        # Returns

        an (edges, warnings) tuple; a warning names a principle that does not exist,
        or a principle in tension with itself, which would hide it from the orphan
        sweep while meaning nothing
        """
        edges: set[Edge] = set()
        warnings: list[str] = []
        for node in nodes.values():
            for other in node.tension:
                if other == node.id:
                    warnings.append(f"{node.id} tensions with itself")
                    continue
                if other not in nodes:
                    warnings.append(f"{node.id} tensions with unknown {other}")
                    continue
                edges.add(Edge(Rel.TENSION, node.id, other))
                edges.add(Edge(Rel.TENSION, other, node.id))
        return edges, warnings

    @staticmethod
    def _orphans(nodes: dict[str, Node], edges: set[Edge]) -> list[str]:
        """one warning per principle no edge touches.

        # Arguments

        * `nodes` - every principle, by id
        * `edges` - the derived edges

        # Returns

        the warnings, one per unreachable principle
        """
        touched = {edge.src for edge in edges} | {edge.dst for edge in edges}
        return [f"{node_id} is an orphan - no edges" for node_id in nodes if node_id not in touched]

    def to_json(self) -> str:
        """the graph as deterministic json text: graph.json's content.

        # Returns

        a json string with a trailing newline, byte-identical per build
        """
        graph = {"nodes": [node.to_dict() for node in self.nodes.values()],
                 "edges": [edge.to_dict() for edge in self.edges],
                 "warnings": self.warnings}
        return json.dumps(graph, indent=2, ensure_ascii=False) + "\n"
