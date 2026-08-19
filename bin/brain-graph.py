#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-graph: build the deterministic knowledge graph from the cards.

    python3 brain-graph.py            build brain/graph/graph.json + graph.cypher
    python3 brain-graph.py --check    build to memory, fail if it drifts from disk

the graph IS the queryable context layer. nodes are the cards, edges are
derived (never authored) from frontmatter and [[wikilinks]]. the Node/Edge
datatypes, the frontmatter parser, and the drift-gate are shared via brainlib -
brain-graph writes Node.to_dict, brain-recall reads Node.from_dict, one
definition. output is byte-identical on re-run, committed, and `--check`-guarded
a neo4j cypher export is emitted too; nothing depends on neo4j

the graph is KNOWLEDGE, kept separate from the execution FLOW (brain-flow.py)

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Artifact, Edge, Frontmatter, Kind, Layout, Node, kind_rank, parse_frontmatter, read_text

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
# every path this tool touches, resolved once by the shared discovery
LAYOUT = Layout.discover()
# the card directories scanned into nodes, with their node kind. voice
# docs are retrieved by name, not graph traversal, so they are not nodes
CARD_DIRS = [(LAYOUT.principles, "principle"), (LAYOUT.intents, "interest")]
# neo4j relationship names for the cypher export; the node labels come from Kind
RELS: dict[str, str] = {"serves": "SERVES", "served_by": "SERVED_BY", "relates": "RELATES", "tension": "TENSION"}

def scalar(front: Frontmatter, key: str, default: str = "") -> str:
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

        >>> scalar({"name": "principle-01"}, "name")
        'principle-01'
        >>> scalar({"tells": ["a", "b"]}, "tells", "?")
        '?'
    """
    value = front.get(key, default)
    return value if isinstance(value, str) else default


def listed(front: Frontmatter, key: str) -> list[str]:
    """one frontmatter field as a list of strings.

    # Arguments
    * `front` - the parsed frontmatter
    * `key` - the field name

    # Returns
    the list value, or an empty list when the field is absent or a scalar

    # Example

        >>> listed({"tells": ["never guess", "ask first"]}, "tells")
        ['never guess', 'ask first']
        >>> listed({"name": "principle-01"}, "name")
        []
    """
    value = front.get(key, [])
    return value if isinstance(value, list) else []


def cypher_label(kind: str) -> str:
    """the neo4j node label for a card kind.

    # Arguments

    * `kind` - the kind string as read from a card

    # Returns

    the kind's label, or `Card` when the kind is unrecognised

    # Example

        >>> cypher_label("principle"), cypher_label("bogus")
        ('Principle', 'Card')
    """
    try:
        return Kind(kind).label
    except ValueError:
        return "Card"


@dataclass
class GraphBuilder(Artifact):
    """builds the knowledge graph (cards -> nodes, derived relationships -> edges)."""

    store: Path = Path()
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def load(self) -> "GraphBuilder":
        """load every card directory into the node table.

        # Returns
        self, for chaining
        """
        # --------------------------------------------------
        # walk each card directory in sorted order
        # --------------------------------------------------
        for directory, kind in CARD_DIRS:
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.md")):
                text = read_text(path)
                front = parse_frontmatter(text)
                node_id = scalar(front, "name", path.stem)
                node = Node(
                    id=node_id,
                    kind=kind,
                    headline=scalar(front, "rule") or scalar(front, "one_line") or path.stem,
                    interest=listed(front, "interest"),
                    confidence=scalar(front, "confidence"),
                    binds=listed(front, "binds"),
                    tells=listed(front, "tells"),
                    tension=listed(front, "tension"),
                    body_links=sorted(set(re.findall(r"\[\[(principle-[a-z0-9-]+)\]\]", text))),
                    path=str(path.relative_to(self.store.parent)),
                )
                self.nodes[node_id] = node
        return self

    def serves_edges(self) -> tuple[set[Edge], list[str]]:
        """the serves edges and their inverse served_by, one pair per interest.

        served_by is the inverse of serves, so each principle declares its
        interests once and the reverse direction is derived - no drift

        # Returns
        an (edges, warnings) tuple; a warning names an interest with no card
        """
        edges: set[Edge] = set()
        warnings: list[str] = []
        for node in self.nodes.values():
            if node.kind != "principle":
                continue
            for interest in node.interest:
                edges.add(Edge("serves", node.id, interest))
                edges.add(Edge("served_by", interest, node.id))
                if interest not in self.nodes:
                    warnings.append(f"{node.id} serves unknown interest {interest}")
        return edges, warnings

    def relates_edges(self) -> tuple[set[Edge], list[str]]:
        """the relates edges, one per [[link]] in a principle's body.

        # Returns
        an (edges, warnings) tuple; a warning names a link with no card
        """
        edges: set[Edge] = set()
        warnings: list[str] = []
        for node in self.nodes.values():
            if node.kind != "principle":
                continue
            for other in node.body_links:
                if other == node.id:
                    continue
                edges.add(Edge("relates", node.id, other))
                if other not in self.nodes:
                    warnings.append(f"{node.id} relates to unknown card {other}")
        return edges, warnings

    def tension_edges(self) -> tuple[set[Edge], list[str]]:
        """the tension edges, symmetric, from each card's `tension:` field.

        # Returns
        an (edges, warnings) tuple; a warning names a card that does not exist
        """
        edges: set[Edge] = set()
        warnings: list[str] = []
        for node in self.nodes.values():
            for other in node.tension:
                edges.add(Edge("tension", node.id, other))
                edges.add(Edge("tension", other, node.id))
                if other not in self.nodes:
                    warnings.append(f"{node.id} tensions with unknown card {other}")
        return edges, warnings

    def orphan_warnings(self, edges: set[Edge]) -> list[str]:
        """one warning per node no edge touches.

        # Arguments
        * `edges` - the derived edge set

        # Returns
        the warnings, one per unreachable node
        """
        touched = {e.src for e in edges} | {e.dst for e in edges}
        return [f"{node_id} is an orphan - no edges" for node_id in self.nodes if node_id not in touched]

    def build(self) -> "GraphBuilder":
        """derive every edge from frontmatter and links, and flag problems.

        # Returns
        self, for chaining
        """
        edges: set[Edge] = set()
        warnings: list[str] = []
        # --------------------------------------------------
        # each relationship kind is derived by its own pass
        # --------------------------------------------------
        for derive in (self.serves_edges, self.relates_edges, self.tension_edges):
            found, complaints = derive()
            edges |= found
            warnings.extend(complaints)
        warnings.extend(self.orphan_warnings(edges))
        # --------------------------------------------------
        # stable order
        # --------------------------------------------------
        self.edges = sorted(edges)
        self.warnings = sorted(set(warnings))
        return self

    def ordered_nodes(self) -> list[Node]:
        """nodes sorted by (kind, id) for stable output.

        # Returns
        the node list in deterministic order
        """
        return sorted(self.nodes.values(), key=lambda n: (kind_rank(n.kind), n.id))

    def to_json(self) -> str:
        """render the graph as deterministic json text.

        # Returns
        a json string with a trailing newline, byte-identical per build
        """
        graph = {"nodes": [n.to_dict() for n in self.ordered_nodes()],
                     "edges": [e.to_dict() for e in self.edges],
                     "warnings": self.warnings}
        return json.dumps(graph, indent=2, ensure_ascii=False) + "\n"

    def to_cypher(self) -> str:
        """render the graph as a deterministic neo4j CREATE script.

        # Returns
        a cypher string; load with `cypher-shell < graph.cypher` for a visual
        """
        lines: list[str] = []
        # --------------------------------------------------
        # node creates, sorted like the json
        # --------------------------------------------------
        for node in self.ordered_nodes():
            headline = node.headline.replace("\\", "\\\\").replace("'", "\\'")
            lines.append(f"CREATE (:{cypher_label(node.kind)} {{id:'{node.id}', headline:'{headline}'}});")
        # --------------------------------------------------
        # relationship creates, in the same stable edge order
        # --------------------------------------------------
        lines.extend(f"MATCH (a {{id:'{edge.src}'}}),(b {{id:'{edge.dst}'}}) "
                     f"CREATE (a)-[:{RELS.get(edge.type, 'LINK')}]->(b);"
                     for edge in self.edges)
        return "\n".join(lines) + "\n"

    def targets(self) -> list[tuple[Path, str]]:
        """the committed artifacts: graph.json and graph.cypher.

        # Returns
        a list of (path, content) pairs
        """
        return [(LAYOUT.graph_json, self.to_json()),
                (LAYOUT.graph_cypher, self.to_cypher())]

    def summary(self) -> str:
        """a one-line (plus warnings) build summary.

        # Returns
        the node/edge/warning counts and any warning lines
        """
        head = (f"brain-graph done -> {self.out_dir}\n"
                f"  nodes: {len(self.nodes)} | edges: {len(self.edges)} | warnings: {len(self.warnings)}")
        return head + "".join(f"\n  warn: {w}" for w in self.warnings)


def main() -> None:
    """build the graph, then either write it or check it against disk."""
    builder = GraphBuilder(out_dir=LAYOUT.graph_dir, store=LAYOUT.store).load().build()
    builder.run(Args.from_argv(), "brain-graph")


if __name__ == "__main__":
    main()
