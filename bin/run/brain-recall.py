#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-recall: retrieve the cards relevant to a task.

    python3 brain-recall.py <<'EOF'
    rust review, dont commit, dont fake the bench
    EOF
    python3 brain-recall.py -n 10 <<'EOF'          pin the scored part of the window to n cards
    python3 brain-recall.py --binds code <<'EOF'   also load every card bound to a context
    python3 brain-recall.py --tells <<'EOF'        every card whose tells contain the phrase
    python3 brain-recall.py --neighbors P09        one node and its edges
    python3 brain-recall.py --all                  dump the index

the task, and the --tells phrase, go on stdin through a quoted heredoc: the
text, then `EOF` on a line of its own. a word in argv is a usage error

the ranking is brainlib.recall's RecallIndex

the index is one line per card. after it, the INLINE_CARDS highest-scored
non-constitution cards that fit INLINE_BYTES print in full - the why and the
how, not only the rule - each at most once per session: a SessionRecord over the
session's ServedLog (brainlib.served) holds the cards this session has been
shown, and a card already shown is marked in the index, with its path, instead
of reprinted. a compaction empties the context, so a card shown before one is
shown again; a subagent shares its parent's session id but not its context, so
the mark tells it to read the path when the text is not in its context

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import (
    ENCODING,
    INLINE_BYTES,
    INLINE_CARDS,
    Args,
    Flag,
    Harness,
    Harnesses,
    Layout,
    Mark,
    RecallIndex,
    ServedLog,
    Tool,
    TranscriptError,
    UsageError,
    find_served,
)

# --------------------------------------------------
# external
# --------------------------------------------------
import datetime as dt
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
# the index line of a card whose full text follows the index
INLINED_MARK = "full text below"
# the index line of a card an earlier recall in this session printed in full
EARLIER_MARK = "full text printed earlier this session"
# the full-text cards are in context or at their path; only the plain one-liners are an index to open
RECALL_FOLLOW_UP = f"""
---
these cards are the rules this work must abide by; the % is how much of the task each explains.
a card marked `{INLINED_MARK}` or `{EARLIER_MARK}` is in your context in full - if not, read its path: apply it as
written. every other one-liner is an INDEX entry - open its path if you judge it relevant, before
doing the state's work. cite each card you applied in the state's output, with the evidence:
`P27: bench/ has 14 files, limit 12`. an uncited card was not applied."""
# every path this tool touches, resolved once by the shared discovery
LAYOUT = Layout.discover()


@dataclass(frozen=True)
class InlinePlan:
    """which cards one recall prints in full, and which this session already holds."""

    # card id to its body, highest score first; printed after the index
    bodies: dict[str, str]
    # the cards an earlier recall in this session printed in full
    earlier: frozenset[str]

    def note(self, node_id: str, path: str) -> str | None:
        """the index line saying where a card's full text is.

        # Arguments
        * `node_id` - the card's id
        * `path` - the card's file, as the index prints it

        # Returns
        INLINED_MARK; EARLIER_MARK with the path to read for an agent that
        shares the session but not its context; None for a card left as a
        one-liner

        # Example

            >>> plan = InlinePlan({"p1": "# P1"}, frozenset({"p2"}))
            >>> plan.note("p1", "p1.md"), plan.note("p3", "p3.md")
            ('full text below', None)
            >>> plan.note("p2", "p2.md")
            'full text printed earlier this session - read p2.md if it is not in your context'
        """
        if node_id in self.bodies:
            return INLINED_MARK
        if node_id in self.earlier:
            return f"{EARLIER_MARK} - read {path} if it is not in your context"
        return None


@dataclass(frozen=True)
class SessionRecord:
    """the cards one session has been shown in full, so each body prints once.

    read from the session's ServedLog (brainlib.served), which every ranked
    recall under a harness appends one Mark to: a later recall in the same
    session marks those cards in the index instead of reprinting them, and the
    next-highest card takes the freed slot. with no session id nothing is
    remembered and every recall prints its top cards in full. a mark a
    compaction erased is not held
    (`ServedLog.held`). the record is a cache - an unreadable or unwritable log
    costs a repeated body, never a crash

    # Example

        >>> import tempfile
        >>> from brainlib import Claude
        >>> cards = {"p1": "# P1", "p2": "# P2"}
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     running, served = (Claude(Path(tmp), Path(tmp)), "s1"), Path(tmp) / "served"
        ...     first, parallel = SessionRecord.load(running, served), SessionRecord.load(running, served)
        ...     plan = first.inline(["p1", "p2"], cards.get, limit=1)
        ...     first.mark(plan.bodies)
        ...     parallel.mark(["p3"])
        ...     after = SessionRecord.load(running, served).inline(["p1", "p2", "p3"], cards.get, limit=1)
        ...     plan
        ...     after.bodies, sorted(after.earlier)
        ...     SessionRecord.load(None, served).inline(["p1", "p2"], cards.get, limit=1)
        InlinePlan(bodies={'p1': '# P1'}, earlier=frozenset())
        ({'p2': '# P2'}, ['p1', 'p3'])
        InlinePlan(bodies={'p1': '# P1'}, earlier=frozenset())
    """

    # the session's log; None with no session id
    log: ServedLog | None = None
    # the marks this session still holds in context
    marks: tuple[Mark, ...] = ()
    # the transcript's end as this recall starts, stamped on the mark it makes
    at: int = 0

    @classmethod
    def load(cls, running: tuple[Harness, str] | None, directory: Path) -> "SessionRecord":
        r"""read one session's record, minus every mark a compaction has erased.

        # Arguments

        * `running` - the harness and session this recall runs in, `Harnesses.running()`
        * `directory` - where the logs live, `find_served()`

        # Returns

        the session's record; unkeyed with no session id or for an id that
        is not a plain file name. with no readable transcript every mark is
        kept, since there is no evidence of a compaction to act on

        # Example

            >>> import tempfile
            >>> from brainlib import Claude
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     running, served = (Claude(Path(tmp), Path(tmp)), "s1"), Path(tmp) / "served"
            ...     log = Path(tmp) / ".claude" / "projects" / "p" / "s1.jsonl"
            ...     log.parent.mkdir(parents=True)
            ...     _ = log.write_text('{"type": "user"}\n')
            ...     SessionRecord.load(running, served).mark(["p1"])
            ...     kept = SessionRecord.load(running, served).seen("p1")
            ...     with log.open("a") as appended:
            ...         _ = appended.write('{"type": "user", "isCompactSummary": true}\n')
            ...     kept, SessionRecord.load(running, served).seen("p1")
            (True, False)
        """
        if running is None or (log := ServedLog.of(running[1], directory)) is None:
            return cls()
        harness, session = running
        try:
            marks = log.marks()
        except OSError as broken:
            print(f"{TOOL}: served log unreadable ({broken}); every card prints in full", file=sys.stderr)
            marks = []
        if (transcript := harness.find(session)) is None:
            return cls(log, tuple(marks))
        try:
            at = transcript.end()
            compactions = transcript.compactions(min(mark.at for mark in marks)) if marks else []
        except TranscriptError as broken:
            # no transcript is no evidence: every mark is kept, and this one
            # stamped at the start so the next recall scans the whole session
            print(f"{TOOL}: {broken}; keeping the record", file=sys.stderr)
            return cls(log, tuple(marks))
        return cls(log, tuple(ServedLog.held(marks, compactions)), at)

    def seen(self, node_id: str) -> bool:
        """whether this session has already been shown a card in full.

        # Arguments
        * `node_id` - the card to check

        # Returns
        True when an earlier recall in this session printed its body
        """
        return any(node_id in mark.cards for mark in self.marks)

    def inline(self, ranked: Sequence[str], body: Callable[[str], str | None],
               limit: int = INLINE_CARDS, budget: int = INLINE_BYTES) -> InlinePlan:
        """choose the cards to print in full: the top unseen readable ones that fit the budget.

        # Arguments
        * `ranked` - candidate card ids, highest score first
        * `body` - a card's full text, or None when it cannot be read
        * `limit` - the most cards to print in full
        * `budget` - the most body bytes to print in full

        # Returns
        at most `limit` unseen cards with a readable body, in rank order, each
        taken while its bytes fit what the budget has left; and every seen one

        # Example

            >>> cards = {"p1": "a" * 10, "p2": "b" * 30, "p3": "c" * 5}
            >>> SessionRecord().inline(["p1", "p2", "p3"], cards.get, budget=20).bodies
            {'p1': 'aaaaaaaaaa', 'p3': 'ccccc'}
        """
        earlier = frozenset(filter(self.seen, ranked))
        bodies: dict[str, str] = {}
        for nid in ranked:
            if len(bodies) == limit:
                break
            if nid in earlier or (text := body(nid)) is None or (size := len(text.encode(ENCODING))) > budget:
                continue
            bodies[nid] = text
            budget -= size
        return InlinePlan(bodies, earlier)

    def mark(self, node_ids: Iterable[str]) -> None:
        """append this recall to the session's log, with the cards it printed in full.

        every ranked recall appends, an empty card set included, so the log
        says recall ran even when every card was already in context. a write
        that fails is reported on stderr and otherwise ignored: the cost is
        those cards printing in full again on the next recall

        # Arguments
        * `node_ids` - the cards just printed in full
        """
        if self.log is None:
            return
        try:
            self.log.append(Mark(self.at, dt.datetime.now(dt.UTC), frozenset(node_ids)))
        except OSError as broken:
            print(f"{TOOL}: served log {self.log.path} not saved ({broken})", file=sys.stderr)


def window_size(args: Args) -> int | None:
    """the exact window `-n` asks for, or None for the dynamic one.

    # Arguments

    * `args` - the parsed command line

    # Returns

    a positive count, or None when `-n` is absent

    # Raises

    UsageError on a value that is not a positive integer, since a negative
    slices from the END and returns MORE cards than asked for, which is the
    opposite of a cap
    """
    if not args.has(Flag.N):
        return None
    raw = args.value(Flag.N)
    if not raw.isdigit() or int(raw) < 1:
        raise UsageError(f"-n takes a positive whole number, not {raw!r}")
    return int(raw)


def contexts(args: Args, index: RecallIndex) -> list[str]:
    """the contexts `--binds` names, whose bound cards always load.

    # Arguments

    * `args` - the parsed command line
    * `index` - the loaded recall index, which knows the contexts its cards bind

    # Returns

    every named context, none when `--binds` is absent

    # Raises

    UsageError on a context no card binds, which would otherwise bind nothing
    in silence
    """
    named = args.values(Flag.BINDS)
    if unknown := sorted(set(named) - index.binds()):
        raise UsageError(f"no card binds {', '.join(unknown)}; cards bind {', '.join(sorted(index.binds()))}")
    return named


def dump_all(index: RecallIndex) -> None:
    """print every node, ranked by kind then id.

    # Arguments
    * `index` - the loaded recall index
    """
    for node_id in sorted(index.nodes, key=index.kind_order):
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


def main(args: Args) -> None:
    """dispatch the requested recall mode.

    `--all`, `--tells` and `--neighbors` are lookups that print and stop; with
    none of them the task on stdin is ranked, the cards this session has not yet
    been shown are inlined, and those bodies are recorded as shown

    # Arguments

    * `args` - the parsed command line; the task text arrives on stdin, and the
      flags pick the mode and the window
    """
    index = RecallIndex.build(LAYOUT)
    # --------------------------------------------------
    # the three lookup modes, each terminal
    # --------------------------------------------------
    if args.has(Flag.ALL):
        dump_all(index)
        return
    if args.has(Flag.TELLS):
        dump_tells(index, args.stdin_text().lower())
        return
    if args.has(Flag.NEIGHBORS):
        dump_neighbors(index, args.value(Flag.NEIGHBORS))
        return
    # --------------------------------------------------
    # ranked recall, then the full-text cards this session has not been shown
    # --------------------------------------------------
    recall = index.recall(args.stdin_text(), window_size(args), contexts(args, index))
    pulled = sum(1 for nid in recall.window if nid in recall.required)
    record = SessionRecord.load(Harnesses.discover().running(), find_served())
    plan = record.inline(recall.featured, index.body)
    # --------------------------------------------------
    # the index, one line per card, then the full text, then the follow-up
    # --------------------------------------------------
    print(f'# brain-recall: "{recall.task}"  ({len(recall.always)} constitution + {len(recall.scored)} scored '
          f'+ {len(recall.bound)} bound + {pulled} required by reference)')
    for node_id in recall.window:
        node = index.nodes[node_id]
        mark, reason = recall.label(node_id)
        print()
        print(f"## [{mark}] {node_id}")
        print(f"-> {node.headline}")
        if reason is not None:
            print(f"   {reason}")
        print(f"   {node.path}")
        if note := plan.note(node_id, node.path):
            print(f"   {note}")
    for body in plan.bodies.values():
        print("\n---\n")
        print(body)
    print(RECALL_FOLLOW_UP)
    record.mark(plan.bodies)


if __name__ == "__main__":
    Tool(TOOL, __doc__, flags=(Flag.ALL, Flag.N, Flag.TELLS, Flag.NEIGHBORS, Flag.BINDS),
         modes=((Flag.ALL,), (Flag.TELLS,), (Flag.NEIGHBORS,), (Flag.N, Flag.BINDS)), stdin=True).run(main)
