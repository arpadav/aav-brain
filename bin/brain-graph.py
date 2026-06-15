#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""brain-graph: build the deterministic knowledge graph from the cards.

    python3 brain-graph.py            build brain/graph/graph.json + graph.cypher
    python3 brain-graph.py --check    build to memory, fail if it drifts from disk

the graph IS the queryable context layer. nodes are the cards, edges are
derived (never authored) from frontmatter and [[wikilinks]]. the Node/Edge
datatypes, the frontmatter parser, and the drift-gate are shared via brainlib -
brain-graph writes Node.to_dict, brain-recall reads Node.from_dict, one
definition. output is byte-identical on re-run, committed, and `--check`-guarded.
a neo4j cypher export is emitted too; nothing depends on neo4j.

the graph is KNOWLEDGE, kept separate from the execution FLOW (brain-flow.py).

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from brainlib import Artifact, Edge, KIND_RANK, Node, parse_frontmatter

# --------------------------------------------------
# constants
# --------------------------------------------------
# the brain store root, relative to this script
STORE = (Path(__file__).resolve().parent / "../brain").resolve()
# the card directories scanned into nodes, with their node kind. voice
# docs are retrieved by name, not graph traversal, so they are not nodes
CARD_DIRS = [(STORE / "principles", "principle"), (STORE / "intents", "interest")]
# neo4j label and relationship names for the cypher export
LABELS = {"principle": "Principle", "interest": "Interest"}
RELS = {"serves": "SERVES", "served_by": "SERVED_BY", "relates": "RELATES", "tension": "TENSION"}

# --------------------------------------------------
# types
# --------------------------------------------------
@dataclass
class GraphBuilder(Artifact):
    """builds the knowledge graph (cards -> nodes, derived relationships -> edges)."""

    store: Path = None
    nodes: dict = field(default_factory=dict)
    edges: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def load(self):
        """load every card directory into the node table.

        # Returns
        self, for chaining.
        """
        # --------------------------------------------------
        # walk each card directory in sorted order
        # --------------------------------------------------
        for directory, kind in CARD_DIRS:
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.md")):
                text = path.read_text(encoding="utf-8")
                front = parse_frontmatter(text)
                node_id = front.get("name", path.stem)
                node = Node(
                    id=node_id,
                    kind=kind,
                    headline=front.get("rule") or front.get("one_line") or path.stem,
                    interest=front.get("interest", []),
                    confidence=front.get("confidence", ""),
                    tells=front.get("tells", []),
                    tension=front.get("tension", []),
                    body_links=sorted(set(re.findall(r"\[\[(principle-[a-z0-9-]+)\]\]", text))),
                    path=str(path.relative_to(self.store.parent)),
                )
                self.nodes[node_id] = node
        return self

    def build(self):
        """derive every edge from frontmatter and links, and flag problems.

        served_by is the inverse of serves, so each principle declares its
        interests once and the reverse direction is derived - no drift.

        # Returns
        self, for chaining.
        """
        edges = set()
        warnings = []
        # --------------------------------------------------
        # serves: principle -> interest, plus its inverse served_by
        # --------------------------------------------------
        for node in self.nodes.values():
            if node.kind == "principle":
                for interest in node.interest:
                    edges.add(Edge("serves", node.id, interest))
                    edges.add(Edge("served_by", interest, node.id))
                    if interest not in self.nodes:
                        warnings.append(f"{node.id} serves unknown interest {interest}")
        # --------------------------------------------------
        # relates: principle -> principle, from body [[links]]
        # --------------------------------------------------
        for node in self.nodes.values():
            if node.kind == "principle":
                for other in node.body_links:
                    if other == node.id:
                        continue
                    edges.add(Edge("relates", node.id, other))
                    if other not in self.nodes:
                        warnings.append(f"{node.id} relates to unknown card {other}")
        # --------------------------------------------------
        # tension: symmetric conflict, from the `tension:` field
        # --------------------------------------------------
        for node in self.nodes.values():
            for other in node.tension:
                edges.add(Edge("tension", node.id, other))
                edges.add(Edge("tension", other, node.id))
                if other not in self.nodes:
                    warnings.append(f"{node.id} tensions with unknown card {other}")
        # --------------------------------------------------
        # orphans: a node no edge touches
        # --------------------------------------------------
        touched = {e.src for e in edges} | {e.dst for e in edges}
        for node_id in self.nodes:
            if node_id not in touched:
                warnings.append(f"{node_id} is an orphan - no edges")
        # --------------------------------------------------
        # stable order
        # --------------------------------------------------
        self.edges = sorted(edges)
        self.warnings = sorted(set(warnings))
        return self

    def ordered_nodes(self):
        """nodes sorted by (kind, id) for stable output.

        # Returns
        the node list in deterministic order.
        """
        return sorted(self.nodes.values(), key=lambda n: (KIND_RANK.get(n.kind, 9), n.id))

    def to_json(self):
        """render the graph as deterministic json text.

        # Returns
        a json string with a trailing newline, byte-identical per build.
        """
        graph = dict(nodes=[n.to_dict() for n in self.ordered_nodes()],
                     edges=[e.to_dict() for e in self.edges],
                     warnings=self.warnings)
        return json.dumps(graph, indent=2, ensure_ascii=False) + "\n"

    def to_cypher(self):
        """render the graph as a deterministic neo4j CREATE script.

        # Returns
        a cypher string; load with `cypher-shell < graph.cypher` for a visual.
        """
        lines = []
        # --------------------------------------------------
        # node creates, sorted like the json
        # --------------------------------------------------
        for node in self.ordered_nodes():
            headline = node.headline.replace("\\", "\\\\").replace("'", "\\'")
            lines.append(f"CREATE (:{LABELS.get(node.kind, 'Card')} {{id:'{node.id}', headline:'{headline}'}});")
        # --------------------------------------------------
        # relationship creates, in the same stable edge order
        # --------------------------------------------------
        for edge in self.edges:
            lines.append(f"MATCH (a {{id:'{edge.src}'}}),(b {{id:'{edge.dst}'}}) "
                         f"CREATE (a)-[:{RELS.get(edge.type, 'LINK')}]->(b);")
        return "\n".join(lines) + "\n"

    def targets(self):
        """the committed artifacts: graph.json and graph.cypher.

        # Returns
        a list of (path, content) pairs.
        """
        return [(self.out_dir / "graph.json", self.to_json()),
                (self.out_dir / "graph.cypher", self.to_cypher())]

    def summary(self):
        """a one-line (plus warnings) build summary.

        # Returns
        the node/edge/warning counts and any warning lines.
        """
        head = (f"brain-graph done -> {self.out_dir}\n"
                f"  nodes: {len(self.nodes)} | edges: {len(self.edges)} | warnings: {len(self.warnings)}")
        return head + "".join(f"\n  warn: {w}" for w in self.warnings)


# --------------------------------------------------
# entrypoint
# --------------------------------------------------
def main():
    """build the graph, then either write it or check it against disk."""
    builder = GraphBuilder(out_dir=STORE / "graph", store=STORE).load().build()
    builder.run(sys.argv, "brain-graph")


if __name__ == "__main__":
    main()
