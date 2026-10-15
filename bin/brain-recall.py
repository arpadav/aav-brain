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
is the constitution (always, unranked) plus every card explaining at least its
tier's SHARE of the task, capped at MAX_N. on top of that window, a card REFERENCED by a returned
card is itself returned - a reference is the author saying these two are read
together, so the returned set is closed under references and a linked card can
never be cut off by rank

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Exit, Flag, Layout, Node, Rel, Tier, kind_rank, load_json

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
# how much of a seed's score a one-hop neighbour inherits, BEFORE the degree
# divisor below. the pair is what makes propagation carry meaning instead of
# popularity: a raw `score * INHERIT` made rank a function of how many other
# cards happened to link at a target, which is authoring convenience, not
# relevance. measured over the real prompt corpus, correlation(in-degree,
# served) was 0.86 against correlation(judged relevance, served) of 0.33 - the
# graph was ranking by fan-in. dividing by the target's in-degree drops the
# first to 0.09. it also costs a little of the second, to 0.30: a ONE-SIDED
# trade, worth taking because the popularity coupling is the larger error, but
# not the two-sided win an earlier version of this comment claimed
INHERIT = 1.0
# the share of a task a card must EXPLAIN to be admitted, as a fraction of the
# task's total information content. an absolute cutoff is only possible on a
# normalised score: under the frequency-counting scorer this replaced, the raw
# top score varied about fifteenfold across real prompts, so one number admitted
# the whole store on a long task and nothing on a short one. dividing by what a
# perfect card would score for THIS task makes the number mean the same thing on
# every task, and makes it readable - 0.30 is
# "this card speaks to a third of what you asked". measured against the real
# corpus it holds the mean window near 14 cards where the score-relative floor
# it replaced returned 26 of 51, at no cost to ranking quality
EXPLAIN_FLOOR = 0.30

# a card CITED by one that matched clears a lower bar than a card that matched
# on its own - the citation is evidence. it is still a bar: unbounded, the pull
# was the larger half of the window and it selects purely on fan-in, which
# reintroduced exactly the popularity coupling the degree divisor removes from
# the scoring path
REFERENCE_FLOOR = 0.12

# and a hard ceiling on it, so one heavily-citing card cannot drag in a crowd
MAX_REFERENCES = 6

# the second admission route, and the one that keeps the floor honest on a big
# request. an absolute share alone starved: a sprawling multi-part ask spans
# more topics than any single card covers, so 15 of 50 real prompts admitted
# NOTHING and fell through to the fallback - 10 of 18 large asks among them,
# which are exactly the prompts with the most relevant cards. a card that is
# clearly the best answer available gets in even when the task is too broad for
# anything to cover a third of it
BEST_SHARE = 0.8

# narrow cards have the LOWEST measured breadth in the store - ten of the
# fourteen were judged relevant on one prompt of fifty, four on none. a floor
# tuned for breadth would never admit one, so they clear on a lower bar. that is
# a bet that a rare card is specific rather than dead (stay-in-the-working-folder
# fires exactly when it should), and tiers.toml records it as a bet, not a
# finding - nothing here measures their precision
NARROW_FLOOR = 0.20
# the most the score window alone may take. there is no lower bound: the
# relative route admits the best card unconditionally, so a floor would only
# ever pad a window that already has its best answer in it
MAX_N = 20
# the edge types a card AUTHORS: [[body links]], `tension:`, `interest:`
# served_by was the DERIVED inverse and is deliberately excluded - intent-craft
# alone carried 27 serves edges, so closing over it returned the whole store
# both are historical: intents are no longer nodes and neither edge is emitted,
# so neither appears here
REFERENCE_EDGES: frozenset[Rel] = frozenset({Rel.RELATES, Rel.TENSION})

@dataclass
class RecallIndex:
    """the built knowledge graph (shared Node objects), indexed for recall."""

    nodes: dict[str, Node] = field(default_factory=dict)
    adjacency: dict[str, list[tuple[str, Rel]]] = field(default_factory=dict)
    # fan-in per node, the divisor that keeps propagation from ranking by
    # popularity; every id is present with a floor of 1 so the divide is total
    in_degree: dict[str, int] = field(default_factory=dict)
    # what a card covering the WHOLE task would score, set by `seed`; the
    # denominator that turns a raw sum into a share and makes a floor absolute
    task_weight: float = 1.0

    @classmethod
    def load(cls, path: Path) -> "RecallIndex":
        """load graph.json into shared Node objects and an adjacency map.

        # Arguments
        * `path` - the graph.json path

        # Returns
        a RecallIndex keyed by node id, adjacency in the graph's edge order, and
        each node's fan-in floored at 1 so `traverse` can always divide by it
        """
        data = load_json(path, "brain-graph")
        nodes = {n["id"]: Node.from_dict(n) for n in data["nodes"]}
        adjacency: dict[str, list[tuple[str, Rel]]] = {node_id: [] for node_id in nodes}
        for edge in data["edges"]:
            if edge["src"] not in adjacency:
                continue
            # an edge type outside the vocabulary means graph.json was written by
            # a different brain-graph than this one; say which, do not traceback
            try:
                rel = Rel(edge["type"])
            except ValueError:
                sys.exit(f"{TOOL}: graph.json has unknown edge type {edge['type']!r}; re-run brain-graph.py")
            if edge["dst"] not in adjacency:
                # the builder no longer writes these, but a graph.json from an
                # older build can still carry one, and an unguarded destination
                # is a KeyError in `traverse`'s in-degree divide
                continue
            adjacency[edge["src"]].append((edge["dst"], rel))
        in_degree = dict.fromkeys(nodes, 0)
        for targets in adjacency.values():
            for dst, _rel in targets:
                if dst in in_degree:
                    in_degree[dst] += 1
        return cls(nodes=nodes, adjacency=adjacency,
                   in_degree={k: max(1, v) for k, v in in_degree.items()})

    def seed(self, tokens: Sequence[str]) -> dict[str, float]:
        """score every node by keyword overlap with the task tokens.

        a token PRESENT in a node's strong fields (tells, headline) counts
        triple and in its weak field (id) once, each token at most once - so a
        card's score is bounded by the task and divides into a real share

        # Arguments
        * `tokens` - the seed tokens

        # Returns
        a dict of node id to positive seed score
        """
        scores: dict[str, float] = {}
        self.task_weight = float(4 * len(set(tokens))) or 1.0
        for node_id, node in self.nodes.items():
            strong = (" ".join(node.tells) + " " + node.headline).lower()
            weak = node_id.lower()
            total = 0
            # --------------------------------------------------
            # accumulate weighted substring hits per token
            # --------------------------------------------------
            # each token counts ONCE, present or not. counting repeats made a
            # card with a long tells list outscore a card that actually covered
            # the task, and it put the score above any fixed ceiling - which is
            # what a share needs to be a share. this is coverage: how much of
            # what he asked does this card speak to
            for token in set(tokens):
                total += 3 if token in strong else 0
                total += 1 if token in weak else 0
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
        # one deterministic hop, each arrival divided by its own fan-in
        # --------------------------------------------------
        for seed_id in sorted(seeds):
            for dst, etype in self.adjacency.get(seed_id, []):
                final[dst] = final.get(dst, 0) + INHERIT * seeds[seed_id] / self.in_degree[dst]
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

    def constitution(self) -> list[str]:
        """the cards that load on every recall, whatever the task is.

        these are not privileged by opinion, they are measured: each was judged
        relevant on a fifth or more of a labelled prompt set while the scorer
        surfaced two of them on 1-2% of real recalls. for a card relevant a
        quarter of the time that retrieval finds one time in fifty, always
        loading beats waiting for a scoring fix. 20% of true relevance shares no
        content token with its card at all; after traversal 4% is still
        unreachable by any score, which is small - the case for the tier rests
        on the measured serving gap, not on unreachability

        # Returns
        the constitution ids, in a stable order
        """
        return sorted(nid for nid, node in self.nodes.items() if node.tier == Tier.CONSTITUTION)

    def explains(self, final: dict[str, float], node_id: str) -> float:
        """what share of the task this card covers, 0..1.

        # Arguments
        * `final` - the combined-score dict
        * `node_id` - the card to measure

        # Returns
        the card's score over what a card covering the whole task would score,
        clamped to 1.0 - inherited score can otherwise carry it past the ceiling
        """
        # clamped: `seed` bounds a card's own score by the task, but `traverse`
        # adds inherited score on top, which took the printed share past 100%
        return min(1.0, final.get(node_id, 0.0) / max(self.task_weight, 1.0))

    def floor_for(self, node_id: str) -> float:
        """the share this card must explain to be admitted, by its tier.

        # Arguments
        * `node_id` - the card to judge

        # Returns
        NARROW_FLOOR for a narrow card, EXPLAIN_FLOOR for every other

        # Example

            >>> RecallIndex().floor_for("absent") == EXPLAIN_FLOOR
            True
        """
        node = self.nodes.get(node_id)
        return NARROW_FLOOR if node is not None and node.tier == Tier.NARROW else EXPLAIN_FLOOR

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

        the constitution loads first and unranked. a card then joins on EITHER
        route: it explains at least its tier's share of the task, or it explains
        at least BEST_SHARE of what the best available card explains. the second
        route exists because the first alone went silent on broad requests -
        nothing covers a third of a six-part ask - and those are the requests
        with the most relevant cards. capped at MAX_N. a task that seeds nothing
        leaves with the constitution alone. cards BOUND to an active context
        join it
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
        # the constitution, ahead of and outside the scored window
        # --------------------------------------------------
        always = [nid for nid in self.constitution() if nid in self.nodes]
        held = set(always)
        # --------------------------------------------------
        # the scored window: an absolute SHARE of the task, per tier
        # --------------------------------------------------
        if pinned is not None:
            window = [nid for nid in ranked if nid not in held][:pinned]
        else:
            scored = [nid for nid in ranked if nid not in held]
            best = max((self.explains(final, nid) for nid in scored), default=0.0)
            window = [nid for nid in scored
                      if self.explains(final, nid) >= self.floor_for(nid)
                      or self.explains(final, nid) >= BEST_SHARE * best][:MAX_N]
            # no fallback is needed: the relative route admits the best card
            # unconditionally (best >= BEST_SHARE * best), so `window` is empty
            # only when `scored` is, and a task that seeds nothing still leaves
            # with the constitution
        window = always + window
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
                if etype not in REFERENCE_EDGES or dst in held or dst in required:
                    continue
                # being cited by a card that matched IS evidence, so the bar is
                # lower than the scored floor - but it is a bar. unbounded, this
                # pull was the larger half of the window and it selects on
                # fan-in by construction, which put back the popularity coupling
                # the degree divisor had just taken out of the scoring path
                if self.explains(final, dst) >= REFERENCE_FLOOR:
                    required[dst] = node_id
        order = sorted(required, key=lambda nid: (-final.get(nid, 0.0), kind_rank(self.nodes[nid].kind), nid))
        return list(window) + order[:MAX_REFERENCES], required

    def neighbors(self, node_id: str) -> list[tuple[str, Rel]]:
        """the edges leaving one node.

        # Arguments
        * `node_id` - the node id

        # Returns
        the adjacency list of (dst, relationship) for that node
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


def window_size(args: Args) -> int | None:
    """the exact window `-n` asks for, or None for the dynamic one.

    # Arguments

    * `args` - the parsed command line

    # Returns

    a positive count, or None when `-n` is absent; exits USAGE on a value that
    is not a positive integer, since a negative slices from the END and returns
    MORE cards than asked for, which is the opposite of a cap
    """
    if not args.has(Flag.N):
        return None
    raw = args.value(Flag.N)
    if not raw.isdigit() or int(raw) < 1:
        print(f"{TOOL}: -n takes a positive whole number, not {raw!r}", file=sys.stderr)
        sys.exit(Exit.USAGE)
    return int(raw)


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
        print(f"{TOOL}: needs a task, or a lookup flag; `--help` lists what it accepts", file=sys.stderr)
        sys.exit(Exit.USAGE)
    args.gate(TOOL, __doc__, Flag.ALL, Flag.N, Flag.TELLS, Flag.NEIGHBORS, Flag.BINDS)
    index = RecallIndex.load(LAYOUT.graph_json)
    # --------------------------------------------------
    # the three lookup modes, each terminal
    # --------------------------------------------------
    if args.has(Flag.ALL):
        dump_all(index)
        return
    if args.has(Flag.TELLS):
        dump_tells(index, args.value(Flag.TELLS).lower())
        return
    if args.has(Flag.NEIGHBORS):
        dump_neighbors(index, args.value(Flag.NEIGHBORS))
        return
    # --------------------------------------------------
    # ranked recall: seed, traverse, rank, emit
    # --------------------------------------------------
    pinned = window_size(args)
    contexts = args.values(Flag.BINDS)
    task = " ".join(args.positional())
    seeds = index.seed(tokenize(task))
    # a task that seeds nothing still gets the cards that do not depend on
    # seeding: the constitution loads on EVERY recall by definition, and a bind
    # is the floor under that. returning early skipped both
    final, why = index.traverse(seeds) if seeds else ({}, {})
    ranked = index.rank(final)
    emit, required = index.select(final, ranked, pinned, contexts)
    always = sum(1 for nid in emit if index.nodes[nid].tier == Tier.CONSTITUTION)
    pulled = sum(1 for nid in emit if nid in required)
    print(f'# brain-recall: "{task}"  ({always} constitution + {len(emit) - always - pulled} scored '
          f'+ {pulled} required by reference)')
    for node_id in emit:
        node = index.nodes[node_id]
        print()
        share = index.explains(final, node_id)
        mark = "always" if node.tier == Tier.CONSTITUTION else f"{share:.0%} of the task"
        print(f"## [{mark}] {node_id}")
        print(f"-> {node.headline}")
        if node_id in required:
            print(f"   REQUIRED by {required[node_id]}")
        elif node_id in why:
            print(f"   {why[node_id]}")
        print(f"   {node.path}")


if __name__ == "__main__":
    main()
