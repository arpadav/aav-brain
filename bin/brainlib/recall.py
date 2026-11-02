"""brainlib.recall: how recall ranks the cards for a task.

brain-recall prints the cards a task gets; brain-misses asks which cards a past
turn would have got. both must rank with the SAME scorer, so the scorer lives
here rather than inside a hyphenated script a second tool would have to copy

it ranks the graph brainlib.graph builds from the cards, in memory on every
call. deterministic: the same task over the same cards always yields the same
window. `RecallIndex.recall` runs the steps in order:
- seed: a task token scores STRONG_HIT in a card's tells or headline and
  WEAK_HIT in its id, each token once
- traverse: each seed passes INHERIT of its score one hop along every edge,
  divided by the receiving card's in-degree
- rank: by score, then kind, then id
- window: the constitution whatever the task; then the cards `admit` lets in -
  its tier's floor or BEST_SHARE of the best candidate's share, at most MAX_N,
  or exactly `pinned` cards; then the cards bound to an active context; then up to
  MAX_REFERENCES cards the window cites that clear REFERENCE_FLOOR
a score is read as the share of the task a card explains (`Scores`), which is
what lets one floor mean the same thing on every task

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.graph import Graph
from brainlib.model import Node
from brainlib.paths import Layout
from brainlib.text import kind_rank, read_text, split_frontmatter
from brainlib.tool import UsageError
from brainlib.vocab import Rel, Tier

# --------------------------------------------------
# external
# --------------------------------------------------
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# how many of a task's cards recall prints in full, highest score first
INLINE_CARDS = 3
# the most bytes of card body one recall prints in full; a card that would cross it stays a one-liner
# 3 cards at the p75 body: of 68 bodies median 2.3 kB, p75 4.0, max 9.0, and the 3 largest are 24.3 kB
INLINE_BYTES = 12_000
# the shortest token worth seeding on; two letters carry no topic
MIN_TOKEN = 3
# tokens too generic to seed on
STOPWORDS: frozenset[str] = frozenset({"the", "and", "for", "you", "with", "that", "this", "dont", "not",
                                       "but", "are", "use", "run", "all", "can", "how", "should"})
# what a task token is worth when a card's tells or headline carry it
STRONG_HIT = 3
# and when only the card's id carries it
WEAK_HIT = 1
# how much of a seed's score a one-hop neighbour inherits, before `traverse`
# divides it by the neighbour's in-degree. the divisor keeps propagation carrying
# meaning instead of popularity: undivided, rank follows how many cards happen
# to link at a target, which is authoring convenience, not relevance. measured
# over the real prompt corpus, undivided propagation gives correlation(in-degree,
# served) 0.86 against correlation(judged relevance, served) 0.33 - the graph
# ranks by fan-in. divided, the first is 0.09 and the second 0.30: a ONE-SIDED
# trade, worth taking because the popularity coupling is the larger error
INHERIT = 1.0
# the share of a task a card must EXPLAIN to be admitted, as a fraction of the
# task's total information content. an absolute cutoff is only possible on a
# normalised score: a raw frequency-counted top score varies about fifteenfold
# across real prompts, so one number would admit the whole store on a long task
# and nothing on a short one. dividing by what a perfect card would score for
# THIS task makes the number mean the same thing on every task, and makes it
# readable - 0.30 is "this card speaks to a third of what you asked"
EXPLAIN_FLOOR = 0.30

# a card CITED by one that matched clears a lower bar than a card that matched
# on its own - the citation is evidence. it is still a bar: unbounded, the pull
# is the larger half of the window and it selects purely on fan-in, which is
# exactly the popularity coupling the degree divisor removes from the scoring
# path
REFERENCE_FLOOR = 0.12

# and a hard ceiling on it, so one heavily-citing card cannot drag in a crowd
MAX_REFERENCES = 3

# the second admission route, and the one that keeps the floor honest on a big
# request. an absolute share alone starves: a sprawling multi-part ask spans
# more topics than any single card covers, so on its own it admitted NOTHING on
# 15 of 50 real prompts - 10 of 18 large asks among them, which are exactly the
# prompts with the most relevant cards. a card that is clearly the best answer
# available gets in even when the task is too broad for anything to cover a
# third of it
BEST_SHARE = 0.8

# narrow cards have the LOWEST measured breadth in the store, so a floor tuned
# for breadth would never admit one and they clear on a lower bar. measured, and
# recorded as a bet rather than a finding: tiers.toml
NARROW_FLOOR = 0.20
# the most the score window alone may take; `-n` pins an exact count and
# bypasses it. it has no lower bound: the relative route admits the best card
# whenever any non-constitution card scores. the ceiling is about attention, not
# relevance: past about ten scored cards the lower ranks sit in the window
# unheeded. over 4595 real prompts (2026-11-02) the whole window,
# references and constitution included, averages 14.6 cards and tops out at 18
MAX_N = 10
# the edges a reference follows
REFERENCE_EDGES: frozenset[Rel] = frozenset({Rel.RELATES, Rel.TENSION})


@dataclass(frozen=True)
class Scores:
    """one task's score per card, over what a card covering the whole task would score.

    # Example

        >>> scores = Scores.of({"p1": 3.0, "p2": 12.0}, ["bench", "fake"])
        >>> scores.weight, scores.explains("p1"), scores.explains("p2"), scores.explains("p3")
        (8.0, 0.375, 1.0, 0.0)
    """

    # card id to its seeded plus inherited score
    final: dict[str, float]
    # the denominator that turns a raw sum into a share and makes a floor absolute
    weight: float = 1.0

    @classmethod
    def of(cls, final: dict[str, float], tokens: Sequence[str]) -> "Scores":
        """a task's scores, weighed against the most a card could score for it.

        # Arguments

        * `final` - card id to combined score
        * `tokens` - the task's seed tokens

        # Returns

        the scores, weighted by every distinct token hitting a card both ways;
        a task with no tokens weighs 1 so the share stays a division

        # Example

            >>> Scores.of({}, []).weight
            1.0
        """
        return cls(final, float((STRONG_HIT + WEAK_HIT) * len(set(tokens))) or 1.0)

    def explains(self, node_id: str) -> float:
        """what share of the task this card covers, 0..1.

        # Arguments

        * `node_id` - the card to measure

        # Returns

        the card's score over what a card covering the whole task would score,
        clamped to 1.0 - inherited score can otherwise carry it past the ceiling

        # Example

            >>> Scores({"p1": 9.0}, 4.0).explains("p1")
            1.0
        """
        # clamped: `seed` bounds a card's own score by the task, but `traverse`
        # adds inherited score on top, which can take the share past 100%
        return min(1.0, self.final.get(node_id, 0.0) / max(self.weight, 1.0))


class RecallError(UsageError):
    """a lookup recall cannot answer: a card token naming no card, or several."""


@dataclass(frozen=True)
class Recall:
    """what one task recalls, in the order recall prints it."""

    task: str
    scores: Scores
    # a pulled-in card's id to the edge that reached it
    why: dict[str, str]
    # the constitution, the scored window, the bound cards, then the references
    window: list[str]
    # every reference that cleared REFERENCE_FLOOR to the card citing it,
    # including the ones past the MAX_REFERENCES cap that window leaves out
    required: dict[str, str]
    # the window outside the constitution, highest score first: the cards
    # whose full text recall prints, the first INLINE_CARDS readable ones within INLINE_BYTES
    featured: list[str]
    # the constitution, which loads whatever the task
    always: list[str]
    # the cards the score admitted, the window's part `-n` pins
    scored: list[str]
    # the cards bound to an active context that the score did not admit
    bound: list[str]
    # BEST_SHARE of the best candidate's share: the relative route's bar,
    # which a pinned window, cut by count, does not apply
    bar: float

    def label(self, node_id: str) -> tuple[str, str | None]:
        """why one windowed card is in the window, as recall prints it.

        # Arguments

        * `node_id` - a card in the window

        # Returns

        the card's mark - `always`, `bound`, or the share of the task it
        explains - and the edge that pulled it in, None for a card loaded
        whatever it scored, which no edge brought

        # Example

            >>> found = Recall("t", Scores({"p2": 2.0}, 8.0), {"p1": "via relates from p2"}, ["p1", "p2"], {},
            ...                ["p2"], ["p1"], [], [], 0.0)
            >>> found.label("p1"), found.label("p2")
            (('always', None), ('25% of the task', None))
        """
        if node_id in self.always:
            return "always", None
        if node_id in self.bound:
            return "bound", None
        if node_id in self.required:
            return f"{self.scores.explains(node_id):.0%} of the task", f"REQUIRED by {self.required[node_id]}"
        return f"{self.scores.explains(node_id):.0%} of the task", self.why.get(node_id)


@dataclass
class RecallIndex:
    """the built knowledge graph (shared Node objects), indexed for recall."""

    # the brain root every node's path is relative to
    root: Path
    nodes: dict[str, Node] = field(default_factory=dict)
    adjacency: dict[str, list[tuple[str, Rel]]] = field(default_factory=dict)
    # fan-in per node, the divisor that keeps propagation from ranking by
    # popularity; every id is present with a floor of 1 so the divide is total
    in_degree: dict[str, int] = field(default_factory=dict)

    @classmethod
    def build(cls, layout: Layout) -> "RecallIndex":
        """the index over the graph built from the layout's cards.

        # Arguments

        * `layout` - the brain whose cards to rank

        # Returns

        a RecallIndex keyed by node id, adjacency in the graph's edge order, and
        each node's fan-in floored at 1 so `traverse` can always divide by it
        """
        graph = Graph.build(layout)
        adjacency: dict[str, list[tuple[str, Rel]]] = {node_id: [] for node_id in graph.nodes}
        in_degree = dict.fromkeys(graph.nodes, 0)
        for edge in graph.edges:
            adjacency[edge.src].append((edge.dst, edge.type))
            in_degree[edge.dst] += 1
        return cls(layout.root, graph.nodes, adjacency, {node_id: max(1, n) for node_id, n in in_degree.items()})

    @staticmethod
    def tokenize(task: str) -> list[str]:
        """split a task string into seed tokens.

        # Arguments

        * `task` - the free-text task description

        # Returns

        lowercase tokens, each at least MIN_TOKEN chars and not a stopword

        # Example

            >>> RecallIndex.tokenize("Refactor the CUDA kernel!")
            ['refactor', 'cuda', 'kernel']
            >>> RecallIndex.tokenize("a of to")
            []
        """
        raw = re.sub(r"[^a-z0-9_ ]", " ", task.lower()).split()
        return [t for t in raw if len(t) >= MIN_TOKEN and t not in STOPWORDS]

    def recall(self, task: str, pinned: int | None = None, contexts: Sequence[str] = ()) -> Recall:
        """the cards one task gets: seed, traverse, rank, admit.

        a task that seeds nothing still gets the cards that do not depend on
        seeding: the constitution loads on EVERY recall by definition, and a
        bind is the floor under that, so an empty seed traverses nothing and
        carries on

        # Arguments

        * `task` - the free-text task description
        * `pinned` - an exact window size, or None for the dynamic one
        * `contexts` - active context tags whose bound cards always load

        # Returns

        the window, its scores, and what pulled each card in

        # Example

            >>> cards = {nid: Node(nid, "principle", f"{nid} rule", [], "high", tells, [], [], f"{nid}.md")
            ...          for nid, tells in (("p1", ["bench numbers"]), ("p2", ["commit"]))}
            >>> index = RecallIndex(Path("."), cards, {"p1": [], "p2": []}, {"p1": 1, "p2": 1})
            >>> found = index.recall("fake the bench", contexts=["code"])
            >>> found.window, found.featured, found.scores.explains("p1"), found.bound
            (['p1'], ['p1'], 0.375, [])
        """
        tokens = self.tokenize(task)
        seeds = self.seed(tokens)
        final, why = self.traverse(seeds) if seeds else ({}, {})
        scores = Scores.of(final, tokens)
        # --------------------------------------------------
        # the constitution, then the scored cards, then the bound ones
        # --------------------------------------------------
        always = self.constitution()
        held = set(always)
        scored, bar = self.admit(scores, [nid for nid in self.rank(final) if nid not in held], pinned)
        held.update(scored)
        bound = [nid for nid in self.bound(contexts) if nid not in held]
        window = always + scored + bound
        # --------------------------------------------------
        # then the references those cards author
        # --------------------------------------------------
        required = self.references(scores, window)
        window += self.rank({nid: final.get(nid, 0.0) for nid in required})[:MAX_REFERENCES]
        featured = self.rank({nid: final.get(nid, 0.0) for nid in window[len(always):]})
        return Recall(task, scores, why, window, required, featured, always, scored, bound, bar)

    def seed(self, tokens: Sequence[str]) -> dict[str, float]:
        """score every node by keyword overlap with the task tokens.

        a token PRESENT in a node's strong fields (tells, headline) counts
        STRONG_HIT and in its weak field (id) WEAK_HIT, each token at most once
        - so a card's score is bounded by the task and divides into a real share

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
            # each token counts at most ONCE. counting repeats would let a card
            # with a long tells list outscore a card that actually covers the
            # task, and would put the score above any fixed ceiling - which is
            # what a share needs to be a share. this is coverage: how much of
            # what he asked does this card speak to
            for token in set(tokens):
                total += STRONG_HIT if token in strong else 0
                total += WEAK_HIT if token in weak else 0
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
            for dst, etype in self.neighbors(seed_id):
                final[dst] = final.get(dst, 0) + INHERIT * seeds[seed_id] / self.in_degree.get(dst, 1)
                if dst not in seeds:
                    why.setdefault(dst, f"via {etype} from {seed_id}")
        return final, why

    def kind_order(self, node_id: str) -> tuple[int, str]:
        """the tie-break every ordering of cards shares: kind, then id.

        # Arguments

        * `node_id` - a card in the index

        # Returns

        the card's (kind rank, id) sort key

        # Example

            >>> card = Node("p1", "interest", "", [], "", [], [], [], "")
            >>> RecallIndex(Path("."), {"p1": card}).kind_order("p1")
            (1, 'p1')
        """
        return kind_rank(self.nodes[node_id].kind), node_id

    def rank(self, final: dict[str, float]) -> list[str]:
        """order scored nodes with a total, reproducible tie-break.

        # Arguments

        * `final` - the combined-score dict

        # Returns

        node ids sorted by descending score, then kind, then id
        """
        return sorted(final, key=lambda nid: (-final[nid], *self.kind_order(nid)))

    def constitution(self) -> list[str]:
        """the cards that load on every recall, whatever the task is.

        measured: tiers.toml

        # Returns

        the constitution ids, in a stable order
        """
        return sorted(nid for nid, node in self.nodes.items() if node.tier == Tier.CONSTITUTION)

    def bar_for(self, node_id: str, bar: float) -> float:
        """the share this card must explain to be admitted: the lower of its tier's floor and the relative bar.

        # Arguments

        * `node_id` - the card to judge
        * `bar` - the relative route's bar, BEST_SHARE of the best candidate

        # Returns

        NARROW_FLOOR for a narrow card, EXPLAIN_FLOOR for every other, or the
        relative bar when it is lower

        # Example

            >>> index = RecallIndex(Path("."))
            >>> index.bar_for("absent", 1.0) == EXPLAIN_FLOOR, index.bar_for("absent", 0.0)
            (True, 0.0)
        """
        node = self.nodes.get(node_id)
        return min(NARROW_FLOOR if node is not None and node.tier == Tier.NARROW else EXPLAIN_FLOOR, bar)

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
        return sorted((nid for nid, node in self.nodes.items() if wanted & set(node.binds)), key=self.kind_order)

    def binds(self) -> set[str]:
        """every context some card binds: the only contexts `bound` can answer for.

        # Returns

        the context tags

        # Example

            >>> card = Node("p1", "principle", "", [], "", [], [], [], "", binds=["code", "python"])
            >>> sorted(RecallIndex(Path("."), {"p1": card}).binds())
            ['code', 'python']
        """
        return {bind for node in self.nodes.values() for bind in node.binds}

    def admit(self, scores: Scores, candidates: Sequence[str], pinned: int | None = None) -> tuple[list[str], float]:
        """the cards the score admits: an absolute share of the task, or a share of the best card.

        a card joins on EITHER route: it explains at least its tier's share of
        the task, or it explains at least BEST_SHARE of what the best candidate
        explains. the second route exists because the first alone goes silent on
        broad requests - nothing covers a third of a six-part ask - and those
        are the requests with the most relevant cards. it admits the best card
        whenever any candidate scores. capped at MAX_N; a pinned count replaces
        both routes and the cap

        # Arguments

        * `scores` - the task's scores
        * `candidates` - the scored card ids outside the constitution, in rank order
        * `pinned` - an exact count from `-n`, or None for the dynamic window

        # Returns

        the admitted ids in rank order, and the relative route's bar

        # Example

            >>> RecallIndex(Path(".")).admit(Scores({"p1": 4.0, "p2": 1.0}, 8.0), ["p1", "p2"])
            (['p1'], 0.4)
        """
        bar = BEST_SHARE * max((scores.explains(nid) for nid in candidates), default=0.0)
        if pinned is not None:
            return list(candidates[:pinned]), bar
        return [nid for nid in candidates if scores.explains(nid) >= self.bar_for(nid, bar)][:MAX_N], bar

    def references(self, scores: Scores, window: Sequence[str]) -> dict[str, str]:
        """the cards the window's cards cite that explain enough of the task to follow.

        being cited by a card that joined IS evidence, so the bar is
        REFERENCE_FLOOR, lower than the scored floor - but a bar. one hop only:
        a second reaches the whole store and stops discriminating

        # Arguments

        * `scores` - the task's scores
        * `window` - the cards already in, in window order

        # Returns

        every reference that cleared REFERENCE_FLOOR to the first card citing
        it, including the ones past the MAX_REFERENCES cap the window leaves out
        """
        held = set(window)
        required: dict[str, str] = {}
        for node_id in window:
            for dst, etype in self.neighbors(node_id):
                if etype not in REFERENCE_EDGES or dst in held or dst in required:
                    continue
                if scores.explains(dst) >= REFERENCE_FLOOR:
                    required[dst] = node_id
        return required

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

        the card whose short id the token names, else the one card whose id
        contains it; raises RecallError when none or several match

        # Example

            >>> cards = [Node(nid, "principle", "", [], "", [], [], [], "")
            ...          for nid in ("principle-08-example", "principle-01-one", "principle-10-ten")]
            >>> index = RecallIndex(Path("."), {card.id: card for card in cards})
            >>> index.resolve("p8"), index.resolve("example"), index.resolve("1")
            ('principle-08-example', 'principle-08-example', 'principle-01-one')
            >>> index.resolve("pp8")  # doctest: +IGNORE_EXCEPTION_DETAIL
            Traceback (most recent call last):
            ...
            brainlib.recall.RecallError: 'pp8' matched 0 cards
        """
        if token in self.nodes:
            return token
        short = f"P{token.lower().removeprefix('p').zfill(2)}"
        matches = ([nid for nid, node in sorted(self.nodes.items()) if node.short_id == short]
                   or [nid for nid in sorted(self.nodes) if token.lower() in nid])
        if len(matches) == 1:
            return matches[0]
        raise RecallError(f"'{token}' matched {len(matches)} cards")

    def body(self, node_id: str) -> str | None:
        """a card's text after its frontmatter, the part recall prints in full.

        # Arguments

        * `node_id` - the card to read

        # Returns

        the body, stripped, or None when the card file cannot be read - a card
        can be moved or deleted after the index is built; a block never closed
        is all body
        """
        try:
            text = read_text(self.root / self.nodes[node_id].path)
        except (OSError, ValueError):
            return None
        split = split_frontmatter(text)
        return (text if split is None else split[1]).strip()

