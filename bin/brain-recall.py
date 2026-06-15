#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""brain-recall: retrieve the cards relevant to a task by walking the graph.

    python3 brain-recall.py "rust review, dont commit, dont fake the bench"
    python3 brain-recall.py --tells unwrap_or     exact tell lookup
    python3 brain-recall.py --neighbors P09        one node and its edges
    python3 brain-recall.py --all                  dump the index
    python3 brain-recall.py -n 10 "<task>"         top n (default 8)

deterministic: keyword-seed the nodes, traverse serves/served_by/relates/
tension edges one hop, rank with a fixed tie-break. same task always yields
the same ranked cards. it reads the Node datatype that brain-graph wrote, from
the shared brainlib (one definition, not a second node representation), and
reads only brain/graph/graph.json - run brain-graph.py first.

Author: aav
"""
# --------------------------------------------------
# external
# --------------------------------------------------
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from brainlib import KIND_RANK, Node, load_json

# --------------------------------------------------
# constants
# --------------------------------------------------
# the built graph this query reads; never re-walks the cards
GRAPH = (Path(__file__).resolve().parent / "../brain/graph/graph.json").resolve()
# tokens too generic to seed on
STOPWORDS = {"the", "and", "for", "you", "with", "that", "this", "dont", "not",
             "but", "are", "use", "run", "all", "can", "how", "should"}
# how much of a seed's score a one-hop neighbour inherits
INHERIT = 0.5
# default number of ranked results to print
TOP_N = 8

# --------------------------------------------------
# types
# --------------------------------------------------
@dataclass
class RecallIndex:
    """the built knowledge graph (shared Node objects), indexed for recall."""

    nodes: dict = field(default_factory=dict)
    adjacency: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path):
        """load graph.json into shared Node objects and an adjacency map.

        # Arguments
        * `path` - the graph.json path.

        # Returns
        a RecallIndex keyed by node id, adjacency in the graph's edge order.
        """
        data = load_json(path, "brain-graph")
        nodes = {n["id"]: Node.from_dict(n) for n in data["nodes"]}
        adjacency = {node_id: [] for node_id in nodes}
        for edge in data["edges"]:
            if edge["src"] in adjacency:
                adjacency[edge["src"]].append((edge["dst"], edge["type"]))
        return cls(nodes=nodes, adjacency=adjacency)

    def seed(self, tokens):
        """score every node by keyword overlap with the task tokens.

        a token in a node's strong fields (tells, headline) counts triple; in
        its weak field (id) it counts once.

        # Arguments
        * `tokens` - the seed tokens.

        # Returns
        a dict of node id to positive seed score.
        """
        scores = {}
        for node_id, node in self.nodes.items():
            strong = (" ".join(node.tells) + " " + node.headline).lower()
            weak = node_id.lower()
            total = 0
            # --------------------------------------------------
            # accumulate weighted substring hits per token
            # --------------------------------------------------
            for token in tokens:
                total += 3 * strong.count(token)
                total += 1 * weak.count(token)
            if total > 0:
                scores[node_id] = total
        return scores

    def traverse(self, seeds):
        """spread a fraction of each seed's score to its one-hop neighbours.

        # Arguments
        * `seeds` - the seed-score dict.

        # Returns
        a (final, why) tuple. final maps node id to total score; why maps a
        pulled-in node id to the edge that reached it.
        """
        final = dict(seeds)
        why = {}
        # --------------------------------------------------
        # one deterministic hop from every seed
        # --------------------------------------------------
        for seed_id in sorted(seeds):
            for dst, etype in self.adjacency.get(seed_id, []):
                final[dst] = final.get(dst, 0) + INHERIT * seeds[seed_id]
                if dst not in seeds:
                    why.setdefault(dst, f"via {etype} from {seed_id}")
        return final, why

    def rank(self, final):
        """order scored nodes with a total, reproducible tie-break.

        # Arguments
        * `final` - the combined-score dict.

        # Returns
        node ids sorted by descending score, then kind, then id.
        """
        return sorted(final, key=lambda nid: (-final[nid], KIND_RANK.get(self.nodes[nid].kind, 9), nid))

    def neighbors(self, node_id):
        """the edges leaving one node.

        # Arguments
        * `node_id` - the node id.

        # Returns
        the adjacency list of (dst, edge-type) for that node.
        """
        return self.adjacency.get(node_id, [])

    def by_tell(self, needle):
        """node ids whose tells contain a substring.

        # Arguments
        * `needle` - the lowercase substring to find.

        # Returns
        the sorted list of matching node ids.
        """
        return [nid for nid in sorted(self.nodes)
                if any(needle in t.lower() for t in self.nodes[nid].tells)]

    def resolve(self, token):
        """resolve a short id like P09 or a substring to a full node id.

        # Arguments
        * `token` - a full id, a Pnn shorthand, or a substring.

        # Returns
        the matching node id, or exits if none or many match.
        """
        if token in self.nodes:
            return token
        short = token.lower().lstrip("p")
        matches = [nid for nid in sorted(self.nodes)
                   if f"principle-{short.zfill(2)}-" in nid or token.lower() in nid]
        if len(matches) == 1:
            return matches[0]
        sys.exit(f"brain-recall: '{token}' matched {len(matches)} nodes")


# --------------------------------------------------
# helpers (pure)
# --------------------------------------------------
def tokenize(task):
    """split a task string into seed tokens.

    # Arguments
    * `task` - the free-text task description.

    # Returns
    lowercase tokens, each at least three chars and not a stopword.
    """
    raw = re.sub(r"[^a-z0-9_ ]", " ", task.lower()).split()
    return [t for t in raw if len(t) >= 3 and t not in STOPWORDS]


# --------------------------------------------------
# entrypoint
# --------------------------------------------------
def main():
    """dispatch the requested recall mode."""
    args = sys.argv[1:]
    if not args:
        sys.exit("usage: brain-recall.py \"<task>\" | --tells <s> | --neighbors <id> | --all [-n N]")
    index = RecallIndex.load(GRAPH)
    # --------------------------------------------------
    # --all: dump every node, ranked by kind then id
    # --------------------------------------------------
    if args[0] == "--all":
        for node_id in sorted(index.nodes, key=lambda nid: (KIND_RANK.get(index.nodes[nid].kind, 9), nid)):
            node = index.nodes[node_id]
            print(f"{node.kind:10} {node_id}  -> {node.headline}")
        return
    # --------------------------------------------------
    # --tells: exact substring lookup over the tells fields
    # --------------------------------------------------
    if args[0] == "--tells":
        for node_id in index.by_tell(" ".join(args[1:]).lower()):
            print(f"{node_id}  -> {index.nodes[node_id].headline}")
        return
    # --------------------------------------------------
    # --neighbors: one node and the edges leaving it
    # --------------------------------------------------
    if args[0] == "--neighbors":
        node_id = index.resolve(args[1])
        print(f"{node_id}  -> {index.nodes[node_id].headline}")
        for dst, etype in index.neighbors(node_id):
            print(f"  -{etype}-> {dst}")
        return
    # --------------------------------------------------
    # ranked recall: seed, traverse, rank, emit
    # --------------------------------------------------
    limit = TOP_N
    if "-n" in args:
        idx = args.index("-n")
        limit = int(args[idx + 1])
        args = args[:idx] + args[idx + 2:]
    seeds = index.seed(tokenize(" ".join(args)))
    if not seeds:
        print(f"no matching cards for: {' '.join(args)}")
        return
    final, why = index.traverse(seeds)
    ranked = index.rank(final)
    print(f"# brain-recall: \"{' '.join(args)}\"  (top {limit})")
    for node_id in ranked[:limit]:
        node = index.nodes[node_id]
        print()
        print(f"## [{round(final[node_id], 1)}] {node_id}")
        print(f"-> {node.headline}")
        if node_id in why:
            print(f"   {why[node_id]}")
        print(f"   {node.path}")


if __name__ == "__main__":
    main()
