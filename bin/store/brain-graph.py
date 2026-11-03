#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""b-graph: write the knowledge graph out as graph.json, and print its warnings.

    b-graph     write brain/graph/graph.json
    b-graph -c  build to memory, fail if it drifts from disk

the graph and its warnings: see brainlib.graph. what graph.json is for: see
schema/optional-graph.md. this is where a human sees the warnings

the graph is KNOWLEDGE, kept separate from the execution FLOW (brain-flow.py)

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Artifact, Exit, Graph, Layout, Tool

# --------------------------------------------------
# external
# --------------------------------------------------
from dataclasses import dataclass

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages
TOOL = Layout.command(Path(__file__))
# the file the graph is written to, inside Layout.graph_dir
GRAPH_JSON = "graph.json"


@dataclass
class GraphFile(Artifact):
    """graph.json: the built graph written out, drift-checked by the shared Artifact harness."""

    graph: Graph

    def targets(self) -> list[tuple[Path, str]]:
        """the one file this export owns.

        # Returns

        the graph.json path and its content
        """
        return [(self.out_dir / GRAPH_JSON, self.graph.to_json())]

    def summary(self) -> str:
        """the node, edge and warning counts, then each warning.

        # Returns

        the summary lines
        """
        # --------------------------------------------------
        # the headline: where it was written and the three counts
        # --------------------------------------------------
        head = (f"{TOOL} done -> {self.out_dir}\n"
                f"  nodes: {len(self.graph.nodes)} | edges: {len(self.graph.edges)} "
                f"| warnings: {len(self.graph.warnings)}")
        # --------------------------------------------------
        # then each warning, one per line
        # --------------------------------------------------
        return head + "".join(f"\n  warn: {warning}" for warning in self.graph.warnings)


def main(args: Args) -> Exit:
    """build the graph, then either write it or check it against disk.

    # Arguments

    * `args` - the parsed command line; `--check` compares instead of writing

    # Returns

    the exit status of writing or checking the graph file
    """
    # --------------------------------------------------
    # find the repo this run is inside
    # --------------------------------------------------
    layout = Layout.discover()
    # --------------------------------------------------
    # build the graph from that repo, then write it or drift-check it per the flags
    # --------------------------------------------------
    return GraphFile(out_dir=layout.graph_dir, graph=Graph.build(layout)).run(args, TOOL)


if __name__ == "__main__":
    Tool.of(TOOL, __doc__).run(main)
