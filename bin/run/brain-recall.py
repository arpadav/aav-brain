#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""b-recall: retrieve the principles relevant to a task.

    b-recall <<'EOF'
    rust review, dont commit, dont fake the bench
    EOF
    b-recall -n 10 <<'EOF'    pin the scored part of the window to n principles
    b-recall -b code <<'EOF'  also load every principle bound to a context
    b-recall -t <<'EOF'       every principle whose tells contain the phrase
    b-recall -e P09           one node and its edges
    b-recall -a               dump the index

the task, and the --tells phrase, go on stdin through a quoted heredoc: the
text, then `EOF` on a line of its own. a word in argv is a usage error

the ranking is brainlib.recall's RecallIndex

the index is one line per principle. after it, the INLINE_PRINCIPLES highest-scored
non-constitution principles that fit INLINE_BYTES print in full - the why and the
how, not only the rule - each at most once per session: a SessionRecord over the
session's SessionLog (brainlib.session) holds the principles this session has been
shown, and a principle already shown is marked in the index, with its path, instead
of reprinted. a compaction empties the context, so a principle shown before one is
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
    INLINE_PRINCIPLES,
    Args,
    Flag,
    Harnesses,
    Layout,
    RecallIndex,
    SessionRecord,
    Tool,
    UsageError,
    XdgLayout,
)

# --------------------------------------------------
# external
# --------------------------------------------------
from collections.abc import Callable, Sequence
from dataclasses import dataclass

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages
TOOL = Layout.command(Path(__file__))
# the index line of a principle whose full text follows the index
INLINED_MARK = "full text below"
# the full-text principles are in context or at their path; only the plain one-liners are an index to open
RECALL_FOLLOW_UP = f"""
---
these principles are the rules this work must abide by; the % is how much of the task each explains.
a principle marked `{INLINED_MARK}` or `{SessionRecord.EARLIER}` is in your context in full - if not, read its
path: apply it as written. every other one-liner is an INDEX entry - open its path if you judge it
relevant, before doing the state's work. cite each principle you applied in the state's output, with the evidence:
`P27: bench/ has 14 files, limit 12`. an uncited principle was not applied."""
# every path this tool touches, resolved once by the shared discovery
LAYOUT = Layout.discover()


@dataclass(frozen=True)
class InlinePlan:
    """which principles one recall prints in full, and which this session already holds."""

    # principle id to its body, highest score first; printed after the index
    bodies: dict[str, str]
    # the principles an earlier recall in this session printed in full
    earlier: frozenset[str]

    def note(self, node_id: str, path: str) -> str | None:
        """the index line saying where a principle's full text is.

        # Arguments
        * `node_id` - the principle's id
        * `path` - the principle's file, as the index prints it

        # Returns
        INLINED_MARK; `SessionRecord.earlier` with the path to read; None for
        a principle left as a one-liner

        # Example

            >>> plan = InlinePlan({"p1": "# P1"}, frozenset({"p2"}))
            >>> plan.note("p1", "p1.md"), plan.note("p3", "p3.md")
            ('full text below', None)
            >>> plan.note("p2", "p2.md")
            'printed in full earlier this session; if it is not in your context: read p2.md'
        """
        if node_id in self.bodies:
            return INLINED_MARK
        if node_id in self.earlier:
            return SessionRecord.earlier(f"read {path}")
        return None

    @classmethod
    def choose(cls, record: SessionRecord, ranked: Sequence[str], body: Callable[[str], str | None],
               limit: int = INLINE_PRINCIPLES, budget: int = INLINE_BYTES) -> "InlinePlan":
        """choose the principles to print in full: the top unseen readable ones that fit the budget.

        # Arguments
        * `record` - what this session has already been shown
        * `ranked` - candidate principle ids, highest score first
        * `body` - a principle's full text, or None when it cannot be read
        * `limit` - the most principles to print in full
        * `budget` - the most body bytes to print in full

        # Returns
        at most `limit` unseen principles with a readable body, in rank order, each
        taken while its bytes fit what the budget has left; and every seen one

        # Example

            >>> import tempfile
            >>> from brainlib import Claude
            >>> principles = {"p1": "a" * 10, "p2": "b" * 30, "p3": "c" * 5}
            >>> InlinePlan.choose(SessionRecord(TOOL), ["p1", "p2", "p3"], principles.get, budget=20).bodies
            {'p1': 'aaaaaaaaaa', 'p3': 'ccccc'}
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     running = (Claude(Path(tmp), Path(tmp)), "s1")
            ...     SessionRecord.load(TOOL, running, XdgLayout(Path(tmp))).mark(["p1"])
            ...     record = SessionRecord.load(TOOL, running, XdgLayout(Path(tmp)))
            ...     InlinePlan.choose(record, ["p1", "p2", "p3"], principles.get, limit=1)
            InlinePlan(bodies={'p2': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'}, earlier=frozenset({'p1'}))
        """
        earlier = frozenset(filter(record.seen, ranked))
        bodies: dict[str, str] = {}
        for nid in ranked:
            if len(bodies) == limit:
                break
            if nid in earlier or (text := body(nid)) is None or (size := len(text.encode(ENCODING))) > budget:
                continue
            bodies[nid] = text
            budget -= size
        return cls(bodies, earlier)


def window_size(args: Args) -> int | None:
    """the exact window `-n` asks for, or None for the dynamic one.

    # Arguments

    * `args` - the parsed command line

    # Returns

    a positive count, or None when `-n` is absent

    # Raises

    UsageError on a value that is not a positive integer, since a negative
    slices from the END and returns MORE principles than asked for, which is the
    opposite of a cap
    """
    if not args.has(Flag.COUNT):
        return None
    raw = args.value(Flag.COUNT)
    if not raw.isdigit() or int(raw) < 1:
        raise UsageError(f"{Flag.COUNT.spelling} takes a positive whole number, not {raw!r}")
    return int(raw)


def contexts(args: Args, index: RecallIndex) -> list[str]:
    """the contexts `--binds` names, whose bound principles always load.

    # Arguments

    * `args` - the parsed command line
    * `index` - the loaded recall index, which knows the contexts its principles bind

    # Returns

    every named context, none when `--binds` is absent

    # Raises

    UsageError on a context no principle binds, which would otherwise bind nothing
    in silence
    """
    named = args.values(Flag.BINDS)
    if unknown := sorted(set(named) - index.binds()):
        raise UsageError(f"no principle binds {', '.join(unknown)}; principles bind {', '.join(sorted(index.binds()))}")
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
    none of them the task on stdin is ranked, the principles this session has not yet
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
    # ranked recall, then the full-text principles this session has not been shown
    # --------------------------------------------------
    recall = index.recall(args.stdin_text(), window_size(args), contexts(args, index))
    pulled = sum(1 for nid in recall.window if nid in recall.required)
    record = SessionRecord.load(TOOL, Harnesses.discover().running(), XdgLayout.discover())
    plan = InlinePlan.choose(record, recall.featured, index.body)
    # --------------------------------------------------
    # the index, one line per principle, then the full text, then the follow-up
    # --------------------------------------------------
    print(f'# {TOOL}: "{recall.task}"  ({len(recall.always)} constitution + {len(recall.scored)} scored '
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
    # every ranked recall appends, an empty set included: brain-misses reads each mark as a recall that ran
    record.mark(plan.bodies.keys())


if __name__ == "__main__":
    Tool.of(TOOL, __doc__, modes=((Flag.ALL,), (Flag.TELLS,), (Flag.NEIGHBORS,), (Flag.COUNT, Flag.BINDS)),
            stdin=True).run(main)
