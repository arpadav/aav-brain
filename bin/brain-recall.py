#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-recall: retrieve the cards relevant to a task by walking the graph.

    python3 brain-recall.py "rust review, dont commit, dont fake the bench"
    python3 brain-recall.py --tells unwrap_or     exact tell lookup
    python3 brain-recall.py --neighbors P09        one node and its edges
    python3 brain-recall.py --all                  dump the index
    python3 brain-recall.py -n 10 "<task>"         pin the window to n cards

deterministic: keyword-seed the nodes, traverse serves/served_by/relates/
tension edges one hop, rank with a fixed tie-break. same task always yields
the same ranked cards. it reads the Node datatype that brain-graph wrote, from
the shared brainlib (one definition, not a second node representation), and
reads only brain/graph/graph.json - run brain-graph.py first

how many cards come back is a property of the task, not a constant: the window
is every card scoring within RELEVANCE_FLOOR of the top card, floored at MIN_N
and capped at MAX_N. on top of that window, a card REFERENCED by a returned
card is itself returned - a reference is the author saying these two are read
together, so the returned set is closed under references and a linked card can
never be cut off by rank

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Flag, Layout, Node, kind_rank, load_json

# --------------------------------------------------
# external
# --------------------------------------------------
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
# every path this tool touches, resolved once by the shared discovery
LAYOUT = Layout.discover()
# the shortest token worth seeding on; two letters carry no topic
MIN_TOKEN = 3
# tokens too generic to seed on
STOPWORDS: set[str] = {"the", "and", "for", "you", "with", "that", "this", "dont", "not",
             "but", "are", "use", "run", "all", "can", "how", "should"}
# how much of a seed's score a one-hop neighbour inherits
INHERIT = 0.5
# a card scoring under this fraction of the top card is not about this task
RELEVANCE_FLOOR = 0.33
# the fewest cards a recall returns, and the most the score window alone may take
MIN_N = 8
MAX_N = 20
# the edge types a card AUTHORS: [[body links]], `tension:`, `interest:`
# served_by is the DERIVED inverse and is deliberately excluded - intent-craft
# alone is served by 21 principles, so closing over it returns the whole store
# (measured: transitive closure over any 8 cards = all 43)
REFERENCE_EDGES: set[str] = {"relates", "tension", "serves"}

@dataclass
class RecallIndex:
    """the built knowledge graph (shared Node objects), indexed for recall."""

    nodes: dict[str, Node] = field(default_factory=dict)
    adjacency: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "RecallIndex":
        """load graph.json into shared Node objects and an adjacency map.

        # Arguments
        * `path` - the graph.json path

        # Returns
        a RecallIndex keyed by node id, adjacency in the graph's edge order
        """
        data = load_json(path, "brain-graph")
        nodes = {n["id"]: Node.from_dict(n) for n in data["nodes"]}
        adjacency: dict[str, list[tuple[str, str]]] = {node_id: [] for node_id in nodes}
        for edge in data["edges"]:
            if edge["src"] in adjacency:
                adjacency[edge["src"]].append((edge["dst"], edge["type"]))
        return cls(nodes=nodes, adjacency=adjacency)

    def seed(self, tokens: Sequence[str]) -> dict[str, float]:
        """score every node by keyword overlap with the task tokens.

        a token in a node's strong fields (tells, headline) counts triple; in
        its weak field (id) it counts once

        # Arguments
        * `tokens` - the seed tokens

        # Returns
        a dict of node id to positive seed score
        """
        scores: dict[str, float] = {}
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

    def traverse(self, seeds: dict[str, float]) -> tuple[dict[str, float], dict[str, str]]:
        """spread a fraction of each seed's score to its one-hop neighbours.

        # Arguments
        * `seeds` - the seed-score dict

        # Returns
        a (final, why) tuple. final maps node id to total score; why maps a
        pulled-in node id to the edge that reached it
        """
        final: dict[str, float] = dict(seeds)
        why: dict[str, str] = {}
        # --------------------------------------------------
        # one deterministic hop from every seed
        # --------------------------------------------------
        for seed_id in sorted(seeds):
            for dst, etype in self.adjacency.get(seed_id, []):
                final[dst] = final.get(dst, 0) + INHERIT * seeds[seed_id]
                if dst not in seeds:
                    why.setdefault(dst, f"via {etype} from {seed_id}")
        return final, why

    def rank(self, final: dict[str, float]) -> list[str]:
        """order scored nodes with a total, reproducible tie-break.

        # Arguments
        * `final` - the combined-score dict

        # Returns
        node ids sorted by descending score, then kind, then id
        """
        return sorted(final, key=lambda nid: (-final[nid], kind_rank(self.nodes[nid].kind), nid))

    def bound(self, contexts: Sequence[str]) -> list[str]:
        """every card that declares itself bound to one of these contexts.

        scoring is word overlap between the task and the card, so a rule phrased
        as a correction scores zero against a task phrased as a request and never
        reaches the writer - measured: the DRY card seeds at 0 for "write python
        scripts". a bind is the floor under that, declared on the card itself

        # Arguments
        * `contexts` - the context tags to bind, e.g. `code`, `python`

        # Returns
        the bound card ids, in rank order of kind then id
        """
        wanted = set(contexts)
        hit = [nid for nid, node in self.nodes.items() if wanted & set(node.binds)]
        return sorted(hit, key=lambda nid: (kind_rank(self.nodes[nid].kind), nid))

    def select(self, final: dict[str, float], ranked: Sequence[str],
               pinned: int | None = None, contexts: Sequence[str] = ()) -> tuple[list[str], dict[str, str]]:
        """the cards a task gets: bound cards, a score-relative window, and references.

        the window is every card within RELEVANCE_FLOOR of the top score, held
        between MIN_N and MAX_N. cards BOUND to an active context join it
        regardless of score, and every card REFERENCED by a windowed card joins
        one hop after - a second hop reaches the whole store and stops
        discriminating

        # Arguments
        * `final` - the combined-score dict
        * `ranked` - node ids in rank order
        * `pinned` - an exact window size from `-n`, or None for the dynamic one
        * `contexts` - active context tags whose bound cards always load

        # Returns
        a (window, required) tuple. window is the ranked ids to emit; required
        maps each reference-pulled id to the card that requires it
        """
        # --------------------------------------------------
        # the score window
        # --------------------------------------------------
        if pinned is not None:
            window = ranked[:pinned]
        else:
            floor = RELEVANCE_FLOOR * final[ranked[0]]
            window = [nid for nid in ranked if final[nid] >= floor][:MAX_N]
            if len(window) < MIN_N:
                window = ranked[:MIN_N]
        # --------------------------------------------------
        # bound cards join the window whatever they scored
        # --------------------------------------------------
        window = list(window) + [nid for nid in self.bound(contexts) if nid not in set(window)]
        # --------------------------------------------------
        # every reference a windowed card authors is required
        # --------------------------------------------------
        held = set(window)
        required: dict[str, str] = {}
        for node_id in window:
            for dst, etype in self.adjacency.get(node_id, []):
                if etype in REFERENCE_EDGES and dst not in held and dst not in required:
                    required[dst] = node_id
        order = sorted(required, key=lambda nid: (-final.get(nid, 0.0), kind_rank(self.nodes[nid].kind), nid))
        return list(window) + order, required

    def neighbors(self, node_id: str) -> list[tuple[str, str]]:
        """the edges leaving one node.

        # Arguments
        * `node_id` - the node id

        # Returns
        the adjacency list of (dst, edge-type) for that node
        """
        return self.adjacency.get(node_id, [])

    def by_tell(self, needle: str) -> list[str]:
        """node ids whose tells contain a substring.

        # Arguments
        * `needle` - the lowercase substring to find

        # Returns
        the sorted list of matching node ids
        """
        return [nid for nid in sorted(self.nodes)
                if any(needle in t.lower() for t in self.nodes[nid].tells)]

    def resolve(self, token: str) -> str:
        """resolve a short id like P09 or a substring to a full node id.

        # Arguments
        * `token` - a full id, a Pnn shorthand, or a substring

        # Returns
        the matching node id, or exits if none or many match
        """
        if token in self.nodes:
            return token
        short = token.lower().lstrip("p")
        matches = [nid for nid in sorted(self.nodes)
                   if f"principle-{short.zfill(2)}-" in nid or token.lower() in nid]
        if len(matches) == 1:
            return matches[0]
        sys.exit(f"{TOOL}: '{token}' matched {len(matches)} nodes")


def tokenize(task: str) -> list[str]:
    """split a task string into seed tokens.

    # Arguments
    * `task` - the free-text task description

    # Returns
    lowercase tokens, each at least three chars and not a stopword

    # Example

        >>> tokenize("Refactor the CUDA kernel!")
        ['refactor', 'cuda', 'kernel']
        >>> tokenize("a of to")
        []
    """
    raw = re.sub(r"[^a-z0-9_ ]", " ", task.lower()).split()
    return [t for t in raw if len(t) >= MIN_TOKEN and t not in STOPWORDS]


def dump_all(index: RecallIndex) -> None:
    """print every node, ranked by kind then id.

    # Arguments
    * `index` - the loaded recall index
    """
    for node_id in sorted(index.nodes, key=lambda nid: (kind_rank(index.nodes[nid].kind), nid)):
        node = index.nodes[node_id]
        print(f"{node.kind:10} {node_id}  -> {node.headline}")


def dump_tells(index: RecallIndex, needle: str) -> None:
    """print every node whose tells contain a substring.

    # Arguments
    * `index` - the loaded recall index
    * `needle` - the lowercase substring to find
    """
    for node_id in index.by_tell(needle):
        print(f"{node_id}  -> {index.nodes[node_id].headline}")


def dump_neighbors(index: RecallIndex, token: str) -> None:
    """print one node and the edges leaving it.

    # Arguments
    * `index` - the loaded recall index
    * `token` - a full id, a Pnn shorthand, or a substring
    """
    node_id = index.resolve(token)
    print(f"{node_id}  -> {index.nodes[node_id].headline}")
    for dst, etype in index.neighbors(node_id):
        print(f"  -{etype}-> {dst}")


def main() -> None:
    """dispatch the requested recall mode."""
    args = Args.from_argv()
    if not args.tokens:
        sys.exit('usage: brain-recall.py "<task>" | --tells <s> | --neighbors <id> | --all [-n N]')
    if unknown := args.unknown(Flag.ALL, Flag.TELLS, Flag.NEIGHBORS, Flag.BINDS):
        sys.exit(f"{TOOL}: unknown flag {unknown[0]}")
    index = RecallIndex.load(LAYOUT.graph_json)
    # --------------------------------------------------
    # the three lookup modes, each terminal
    # --------------------------------------------------
    if args.has(Flag.ALL):
        dump_all(index)
        return
    if args.has(Flag.TELLS):
        dump_tells(index, " ".join(args.tokens[1:]).lower())
        return
    if args.has(Flag.NEIGHBORS):
        dump_neighbors(index, args.value(Flag.NEIGHBORS))
        return
    # --------------------------------------------------
    # ranked recall: seed, traverse, rank, emit
    # --------------------------------------------------
    pinned = int(args.value(Flag.N)) if args.has(Flag.N) else None
    contexts = args.values(Flag.BINDS)
    task = " ".join(args.positional(Flag.N, Flag.BINDS))
    seeds = index.seed(tokenize(task))
    if not seeds:
        print(f"no matching cards for: {task}")
        return
    final, why = index.traverse(seeds)
    ranked = index.rank(final)
    emit, required = index.select(final, ranked, pinned, contexts)
    scored = len(emit) - len(required)
    print(f'# brain-recall: "{task}"  ({scored} in window + {len(required)} required by reference)')
    for node_id in emit:
        node = index.nodes[node_id]
        print()
        print(f"## [{round(final.get(node_id, 0.0), 1)}] {node_id}")
        print(f"-> {node.headline}")
        if node_id in required:
            print(f"   REQUIRED by {required[node_id]}")
        elif node_id in why:
            print(f"   {why[node_id]}")
        print(f"   {node.path}")


if __name__ == "__main__":
    main()
