#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-misses: the turns the brain should have caught since its last review.

    python3 brain-misses.py                               since the newest brain-self-refine trace entry
    python3 brain-misses.py --since 2026-10-31T00:00:00Z  since that instant

reads his heated, interrupting and rejecting turns out of the evidence corpus,
one row per distinct text said in the window, and prints beside each the cards
recall ranks highest for it (brainlib.recall), and whether recall's own log
(brainlib.served) holds a recall in that session that no compaction had erased
by the turn, so its cards could still have been in the turn's context. a turn
the log cannot speak for - said before recording began on this machine, in a
session whose transcript is not on this machine, or in a harness that exports
no session id - is `not recorded`. a card that fits a row
is a finding: the rule existed and was not served, or was served and not applied

FINDINGS when any row is listed

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
    INLINE_CARDS,
    Args,
    DataLayout,
    Exit,
    Flag,
    Harness,
    Harnesses,
    Layout,
    Ledger,
    NoVerdict,
    RecallIndex,
    Record,
    ServedLog,
    Tool,
    TranscriptError,
    UsageError,
    clip,
    find_served,
    parse_iso,
)

# --------------------------------------------------
# external
# --------------------------------------------------
import datetime as dt
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
# every path inside the brain, spelled once (brainlib.Layout)
LAYOUT = Layout.discover()
# the skill whose trace entries mark a review of the brain: the window opens at the newest
REVIEW_SKILL = "brain-self-refine"
# how much of a turn's text one row shows
TEXT_WIDTH = 100
# a row's instant, to the minute
ROW_STAMP = "%Y-%m-%dT%H:%M"
# the instant the window opens after, to the second, in utc
WINDOW_STAMP = "%Y-%m-%dT%H:%M:%SZ"


class EvidenceError(NoVerdict):
    """a corpus file the report reads is absent: brain-extract has not written it here."""


class Served(StrEnum):
    """whether recall's log holds a recall a row's turn could still see the cards of."""

    YES = "yes"
    NO = "no"
    # the log cannot answer: the turn predates recording, its session ran on another machine, or its
    # harness exports no session id
    UNRECORDED = "not recorded"
    # the session's log or transcript cannot be read
    UNREADABLE = "unreadable"


@dataclass(frozen=True)
class Miss:
    """one turn of his the brain should have caught."""

    at: dt.datetime
    # the harness the turn was said in, which knows where its transcript is
    harness: Harness
    project: str
    session: str
    # the turn's text, whitespace collapsed onto one line
    text: str

    @staticmethod
    def words(row: dict[str, Any]) -> str:
        r"""an evidence row's text, whitespace collapsed onto one line.

        # Arguments

        * `row` - a record of heat.jsonl, interruptions.jsonl or rejections.jsonl

        # Returns

        the text, empty when the row carries none

        # Example

            >>> Miss.words({"text": " no\n  stop "})
            'no stop'
        """
        return clip(str(row.get("text") or ""))

    @classmethod
    def from_row(cls, row: dict[str, Any], harnesses: Harnesses) -> "Miss | None":
        """one evidence row as a miss.

        # Arguments

        * `row` - a record of heat.jsonl, interruptions.jsonl or rejections.jsonl
        * `harnesses` - the harnesses a row's `src` may name

        # Returns

        the miss, or None when the row carries no readable ts, no text, or a
        `src` naming no known harness

        # Example

            >>> harnesses = Harnesses.discover(Path("/nonexistent"))
            >>> row = {"ts": "2026-10-31T17:22:44Z", "src": "claude", "proj": "p", "session": "s", "text": "stop"}
            >>> miss = Miss.from_row(row, harnesses)
            >>> miss.at.isoformat(), miss.harness.NAME, miss.project, miss.session, miss.text
            ('2026-10-31T17:22:44+00:00', 'claude', 'p', 's', 'stop')
            >>> Miss.from_row({**row, "ts": ""}, harnesses), Miss.from_row({**row, "src": "x"}, harnesses)
            (None, None)
        """
        # --------------------------------------------------
        # read the row's text, instant and harness
        # --------------------------------------------------
        text, at = cls.words(row), parse_iso(str(row.get("ts") or ""))
        harness = harnesses.named(str(row.get("src") or ""))
        # --------------------------------------------------
        # a row missing any of them cannot be placed
        # --------------------------------------------------
        if at is None or harness is None or not text:
            return None
        return cls(at, harness, str(row.get("proj") or ""), str(row.get("session") or ""), text)

    def excerpt(self) -> str:
        """the turn's text cut to one row, marked when cut.

        # Returns

        at most TEXT_WIDTH characters of the text, quoted

        # Example

            >>> at, claude = dt.datetime(2026, 1, 1, tzinfo=dt.UTC), Harnesses.discover(Path("/a")).all[0]
            >>> Miss(at, claude, "p", "s", "x" * (TEXT_WIDTH + 1)).excerpt() == '"' + "x" * TEXT_WIDTH + '..."'
            True
            >>> Miss(at, claude, "p", "s", "short").excerpt()
            '"short"'
        """
        cut = "..." if len(self.text) > TEXT_WIDTH else ""
        return f'"{self.text[:TEXT_WIDTH]}{cut}"'


@dataclass
class MissReport:
    r"""the turns since a review, each beside the cards recall serves for it.

    # Example

        >>> from brainlib import Node
        >>> at = dt.datetime(2026, 10, 31, 17, 22, tzinfo=dt.UTC)
        >>> card = Node("p61", "principle", "tailnet url stays out", [], "", [], [], [], "")
        >>> index = RecallIndex(Path("."), {"p61": card}, {"p61": []}, {"p61": 1})
        >>> claude = Harnesses.discover(Path("/nonexistent")).all[0]
        >>> misses = [Miss(at, claude, "-home", "fbffe8d9-cd2b", "the tailnet url")]
        >>> report = MissReport(misses, 0, index, Path("/nonexistent"), None)
        >>> print("\n".join(report.describe(report.misses[0])))
        2026-10-31T17:22  -home  fbffe8d9  recall: not recorded
          "the tailnet url"
           75%  p61
    """

    # the turns in the window, one per distinct text at its earliest stamp there, oldest first
    misses: list[Miss]
    # the distinct texts in the whole corpus no row places: no readable ts or no known harness
    skipped: int
    index: RecallIndex
    # recall's logs, find_served()
    served: Path
    # when recording began on this machine, ServedLog.since; None when nothing is recorded yet
    recorded: dt.datetime | None
    # each session's compacting lines, read once however many of its turns are listed; None when unreadable
    compacted: dict[str, list[Record] | None] = field(default_factory=dict)

    @staticmethod
    def last_review(decisions: Path) -> dt.datetime | None:
        """when the brain was last reviewed: the newest self-refine trace entry not pruned stale.

        # Arguments

        * `decisions` - the decision trace

        # Returns

        that entry's instant, or None when the trace holds none

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     trace = Ledger(Path(tmp) / "decisions.jsonl")
            ...     _ = trace.append({"ts": "2026-11-02T00:01:38Z", "skill": REVIEW_SKILL})
            ...     _ = trace.append({"ts": "2026-11-03T00:00:00Z", "skill": REVIEW_SKILL, "stale": True})
            ...     _ = trace.append({"ts": "2026-11-04T00:00:00Z", "skill": "brain-plan"})
            ...     MissReport.last_review(trace.path), MissReport.last_review(Path(tmp) / "absent.jsonl")
            (datetime.datetime(2026, 11, 2, 0, 1, 38, tzinfo=datetime.timezone.utc), None)
        """
        # --------------------------------------------------
        # the instants of the review entries still standing
        # --------------------------------------------------
        stamps = (parse_iso(str(row.get("ts") or "")) for row in Ledger(decisions).read()
                  if row.get("skill") == REVIEW_SKILL and not row.get("stale"))
        return max((stamp for stamp in stamps if stamp is not None), default=None)

    @classmethod
    def collect(cls, since: dt.datetime | None, data: DataLayout,
                index: RecallIndex, harnesses: Harnesses, served: Path) -> "MissReport":
        """every distinct heated, interrupting or rejecting turn said after an instant.

        the three corpora overlap - a heated turn is also a rejection - so a
        text is listed once, at its earliest stamp inside the window; a text
        also said before the window is still listed

        # Arguments

        * `since` - the window opens after this instant; None takes the whole corpus
        * `data` - the private data dir holding the evidence corpus
        * `index` - the recall index to rank each turn with
        * `harnesses` - the harnesses a row's `src` may name
        * `served` - recall's logs, find_served()

        # Returns

        the report over the window

        # Raises

        EvidenceError when one of the three corpus files is absent

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     evidence = DataLayout(Path(tmp)).evidence
            ...     row = {"ts": "2026-10-31T17:22:44Z", "src": "claude", "session": "s1", "text": "stop"}
            ...     _ = Ledger(evidence.heat).append(row)
            ...     _ = Ledger(evidence.rejections).append({**row, "ts": "2026-10-30T09:00:00Z"})
            ...     _ = Ledger(evidence.rejections).append({**row, "ts": "2026-10-30T09:00:00Z", "text": "old"})
            ...     _ = Ledger(evidence.interruptions).append({**row, "ts": "", "text": "undated"})
            ...     _ = Ledger(evidence.interruptions).append({**row, "ts": "", "text": "old"})
            ...     since = dt.datetime(2026, 10, 31, tzinfo=dt.UTC)
            ...     report = MissReport.collect(since, DataLayout(Path(tmp)), RecallIndex(Path(".")),
            ...                                 Harnesses.discover(Path(tmp)), Path(tmp))
            ...     [(miss.text, miss.at.day) for miss in report.misses], report.skipped
            ([('stop', 31)], 1)
            >>> try:
            ...     _ = MissReport.collect(None, DataLayout(Path("/nonexistent")), RecallIndex(Path(".")),
            ...                            Harnesses.discover(Path("/nonexistent")), Path("/nonexistent"))
            ... except EvidenceError as absent:
            ...     print(absent)
            no evidence at /nonexistent/evidence/heat.jsonl; run brain-extract
        """
        # --------------------------------------------------
        # the three evidence ledgers; a missing one means extraction has not run, so there is no verdict
        # --------------------------------------------------
        evidence = data.evidence
        sources = (evidence.heat, evidence.interruptions, evidence.rejections)
        if (absent := next((path for path in sources if not path.exists()), None)) is not None:
            raise EvidenceError(f"no evidence at {absent}; run brain-extract")
        # --------------------------------------------------
        # every row of every ledger
        # --------------------------------------------------
        rows = [row for path in sources for row in Ledger(path).read()]
        # --------------------------------------------------
        # accumulators: the earliest miss per text, and the texts placed or not
        # --------------------------------------------------
        earliest: dict[str, Miss] = {}
        placed: set[str] = set()
        unplaced: set[str] = set()
        # --------------------------------------------------
        # keep each distinct text at its earliest stamp inside the window
        # --------------------------------------------------
        for row in rows:
            miss = Miss.from_row(row, harnesses)
            if miss is None:
                unplaced.add(Miss.words(row))
                continue
            placed.add(miss.text)
            if (since is None or miss.at > since) and (miss.text not in earliest or miss.at < earliest[miss.text].at):
                earliest[miss.text] = miss
        # --------------------------------------------------
        # a text that some other row placed is not skipped
        # --------------------------------------------------
        skipped = unplaced - placed - {""}
        return cls(sorted(earliest.values(), key=lambda miss: miss.at), len(skipped), index, served,
                   ServedLog.since(served))

    def served_state(self, miss: Miss) -> Served:
        r"""whether recall's log holds a recall in the turn's session that no compaction erased by the turn.

        # Arguments

        * `miss` - the turn

        # Returns

        UNRECORDED when the log cannot speak for the turn - the logs are this
        machine's, so a session with no transcript here is one of them - NO
        when no recall preceded it, else YES or NO by `ServedLog.held`;
        UNREADABLE when the log or, past a recall, the transcript cannot be read

        # Example

            >>> import tempfile
            >>> from brainlib import Claude, Mark
            >>> day = lambda n: dt.datetime(2026, 11, n, tzinfo=dt.UTC)
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     claude, codex = Claude(Path(tmp), Path(tmp)), Harnesses.discover(Path(tmp)).named("codex")
            ...     for session in ("s1", "s2"):
            ...         transcript = Path(tmp) / ".claude" / "projects" / "p" / f"{session}.jsonl"
            ...         transcript.parent.mkdir(parents=True, exist_ok=True)
            ...         _ = transcript.write_text('{"type": "user"}\n')
            ...     ServedLog.of("s1", Path(tmp)).append(Mark(16, day(2), frozenset({"p1"})))
            ...     report = MissReport([], 0, RecallIndex(Path(".")), Path(tmp), day(2))
            ...     [str(report.served_state(Miss(day(n), harness, "p", session, "stop")))
            ...      for n, harness, session in ((3, claude, "s1"), (3, claude, "s2"), (1, claude, "s1"),
            ...                                  (3, codex, "s1"), (3, claude, "s3"))]
            ['yes', 'no', 'not recorded', 'not recorded', 'not recorded']
        """
        # --------------------------------------------------
        # a turn with no log, session id, recording or transcript to compare against cannot be answered
        # --------------------------------------------------
        log = ServedLog.of(miss.session, self.served)
        if (log is None or miss.harness.SESSION_ENV is None or self.recorded is None or miss.at < self.recorded
                or (transcript := miss.harness.find(miss.session)) is None):
            return Served.UNRECORDED
        try:
            # --------------------------------------------------
            # the recalls made before the turn
            # --------------------------------------------------
            earlier = ServedLog.held(log.marks(), (), miss.at)
        except OSError as broken:
            print(f"{TOOL}: served log unreadable ({broken})", file=sys.stderr)
            return Served.UNREADABLE
        # --------------------------------------------------
        # nothing was recalled before the turn
        # --------------------------------------------------
        if not earlier:
            return Served.NO
        # --------------------------------------------------
        # read each session's compactions once
        # --------------------------------------------------
        if miss.session not in self.compacted:
            try:
                self.compacted[miss.session] = transcript.compactions()
            except TranscriptError as broken:
                print(f"{TOOL}: {broken}", file=sys.stderr)
                self.compacted[miss.session] = None
        # --------------------------------------------------
        # were any of those recalls still in context after the compactions
        # --------------------------------------------------
        compactions = self.compacted[miss.session]
        if compactions is None:
            return Served.UNREADABLE
        return Served.YES if ServedLog.held(earlier, compactions, miss.at) else Served.NO

    def describe(self, miss: Miss) -> list[str]:
        """one turn's rows: where it was said, what was said, what recall serves.

        # Arguments

        * `miss` - the turn

        # Returns

        a header line, the text, then each of recall's INLINE_CARDS
        highest-ranked cards outside the constitution, with the share of the
        turn it explains
        """
        # --------------------------------------------------
        # the cards recall would have ranked for this text
        # --------------------------------------------------
        found = self.index.recall(miss.text)
        cards = [f"  {found.scores.explains(nid):4.0%}  {nid}" for nid in found.featured[:INLINE_CARDS]]
        # --------------------------------------------------
        # the row: when, where, and whether recall served it
        # --------------------------------------------------
        header = (f"{miss.at.strftime(ROW_STAMP)}  {miss.project}  {miss.harness.short(miss.session)}  "
                  f"recall: {self.served_state(miss)}")
        return [header, f"  {miss.excerpt()}", *(cards or ["  no card scored"])]

    def show(self, since: dt.datetime | None) -> None:
        """print every turn, then one summary line.

        # Arguments

        * `since` - the instant the window opens after, for the summary
        """
        # --------------------------------------------------
        # one block per miss
        # --------------------------------------------------
        for miss in self.misses:
            print("\n".join(self.describe(miss)))
            print()
        # --------------------------------------------------
        # the window the list covers, and how much was left out of it
        # --------------------------------------------------
        opened = (f"since {since.astimezone(dt.UTC).strftime(WINDOW_STAMP)}" if since is not None
                  else "in the whole corpus")
        print(f"{TOOL}: {len(self.misses)} turn(s) {opened}; {self.skipped} distinct text(s) in the whole corpus "
              f"skipped, with no readable ts or known harness")


def main(args: Args) -> Exit:
    """list the turns since the last review; FINDINGS when there are any.

    the window opens at `--since` when given, else at the last review recorded
    in the decision trace

    # Arguments

    * `args` - the parsed command line; `--since` is an iso-8601 instant

    # Returns

    `Exit.FINDINGS` when the report lists any miss, else `Exit.OK`; a `--since`
    that does not parse raises `UsageError`
    """
    # --------------------------------------------------
    # the window opens at --since, else at the last review of the brain
    # --------------------------------------------------
    data = DataLayout.discover()
    given = args.value(Flag.SINCE)
    since = parse_iso(given) if given else MissReport.last_review(data.decisions)
    if given and since is None:
        raise UsageError(f"--since takes an iso-8601 instant, not {given!r}")
    # --------------------------------------------------
    # collect, list, and fail when any turn is listed
    # --------------------------------------------------
    report = MissReport.collect(since, data, RecallIndex.build(LAYOUT), Harnesses.discover(), find_served())
    report.show(since)
    return Exit.FINDINGS if report.misses else Exit.OK


if __name__ == "__main__":
    Tool(TOOL, __doc__, flags=(Flag.SINCE,)).run(main)
