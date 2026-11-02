"""brainlib.graph: the principle cards as a graph, built from the cards on every call.

nodes: one per principle card, of kind `Kind.PRINCIPLE`, keyed by its `name:`
or else its file stem, a later duplicate replacing an earlier one. `Graph.build`
says why intents and voice docs are not nodes

edges: derived from the cards, never authored; `Rel` is the closed set
- `relates`: one per `[[principle-...]]` link anywhere in a card's file, to the
  card it names
- `tension`: one each way for every card named in a card's `tension:` field

warnings: a link or tension naming no card, which gets no edge; a card in
tension with itself; an orphan no edge touches

determinism: nodes in (kind, id) order, edges sorted by (type, src, dst),
warnings sorted and deduplicated, so `Graph.to_json` is byte-identical for the
same cards

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.model import Edge, Node
from brainlib.paths import Layout
from brainlib.text import kind_rank
from brainlib.vocab import Kind, Rel

# --------------------------------------------------
# external
# --------------------------------------------------
import json
from dataclasses import dataclass

@dataclass(frozen=True)
class Graph:
    r"""the principle cards as nodes and the links between them as edges, derived, never authored.

    # Example

        >>> import tempfile
        >>> from pathlib import Path
        >>> with tempfile.TemporaryDirectory() as folder:
        ...     layout = Layout(Path(folder))
        ...     layout.principles.mkdir(parents=True)
        ...     card = "---\nname: principle-{}\ntension: [{}]\n---\n{}\n"
        ...     _ = (layout.principles / "a.md").write_text(card.format("a", "principle-b", "[[principle-b]]"))
        ...     _ = (layout.principles / "b.md").write_text(card.format("b", "", "[[principle-x]]"))
        ...     graph = Graph.build(layout)
        ...     _ = (layout.principles / "c.md").write_text(card.format("b", "", ""))
        ...     Graph.build(layout).warnings[0]
        'principle-b is named by both brain/principles/b.md and brain/principles/c.md; brain/principles/c.md is kept'
        >>> for edge in graph.edges:
        ...     print(edge.type, edge.src, edge.dst)
        relates principle-a principle-b
        tension principle-a principle-b
        tension principle-b principle-a
        >>> graph.warnings
        ['principle-b relates to unknown card principle-x']
    """

    # in (kind, id) order: the order graph.json and recall both use
    nodes: dict[str, Node]
    # sorted by (type, src, dst)
    edges: list[Edge]
    # sorted, deduplicated
    warnings: list[str]

    @classmethod
    def build(cls, layout: Layout) -> "Graph":
        """read every card in the layout's principles and derive the edges between them.

        brain/intents/ is deliberately not read: an intent is the WHY of its
        principles and never fires independently, so as a peer node it could
        only ever co-occur with them. measured on a labelled prompt set,
        intent-comprehension and P11 were relevant on 86% of the same prompts
        while sharing 12% of their vocabulary - two nodes, one rule. five of the
        seven highest-overlap card pairs in the store paired an intent with a
        principle. the intent files remain prose a human reads and valid
        [[link]] targets, and each principle's `interest:` field carries the
        association without a node to hang it on. voice docs are retrieved by
        name, not traversal, so they are not nodes either

        # Arguments

        * `layout` - the brain whose cards to read; a missing principles
          directory reads as no cards

        # Returns

        the graph, its warnings naming each duplicate name, unknown link, self-tension and orphan
        """
        # --------------------------------------------------
        # one node per card, a later duplicate name replacing an earlier one
        # --------------------------------------------------
        read: dict[str, Node] = {}
        duplicates: list[str] = []
        for path in sorted(layout.principles.glob("*.md")):
            node = Node.from_card(path, Kind.PRINCIPLE, layout.root)
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
        """the relates edges, one per [[link]] in a card's file.

        # Arguments

        * `nodes` - every card, by id

        # Returns

        an (edges, warnings) tuple; a warning names a link with no card, which
        gets no edge, so no reader has to guard a destination that is not there
        """
        edges: set[Edge] = set()
        warnings: list[str] = []
        for node in nodes.values():
            for other in node.body_links:
                if other == node.id:
                    continue
                if other not in nodes:
                    warnings.append(f"{node.id} relates to unknown card {other}")
                    continue
                edges.add(Edge(Rel.RELATES, node.id, other))
        return edges, warnings

    @staticmethod
    def _tensions(nodes: dict[str, Node]) -> tuple[set[Edge], list[str]]:
        """the tension edges, symmetric, from each card's `tension:` field.

        # Arguments

        * `nodes` - every card, by id

        # Returns

        an (edges, warnings) tuple; a warning names a card that does not exist,
        or a card in tension with itself, which would hide it from the orphan
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
                    warnings.append(f"{node.id} tensions with unknown card {other}")
                    continue
                edges.add(Edge(Rel.TENSION, node.id, other))
                edges.add(Edge(Rel.TENSION, other, node.id))
        return edges, warnings

    @staticmethod
    def _orphans(nodes: dict[str, Node], edges: set[Edge]) -> list[str]:
        """one warning per card no edge touches.

        # Arguments

        * `nodes` - every card, by id
        * `edges` - the derived edges

        # Returns

        the warnings, one per unreachable card
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
