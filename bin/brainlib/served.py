"""brainlib.served: what recall served each session, owned once.

recall appends one Mark per ranked recall to its session's ServedLog, and the
misses report reads the logs back: the record of a run comes from the one
process that knows it ran, never from a guess at a shell command's text. the
logs live in `find_served()`, outside every repo

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.paths import plain_name
from brainlib.text import parse_iso
from brainlib.transcript import Record
from brainlib.vocab import ENCODING

# --------------------------------------------------
# external
# --------------------------------------------------
import datetime as dt
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# a session's log file: the session id, then this
LOG_SUFFIX = ".jsonl"


@dataclass(frozen=True)
class Mark:
    """one recall in a session: where its output starts, when it ran, which cards it printed in full."""

    # the transcript's end when the recall started: its output lies past this byte
    at: int
    # utc
    ts: dt.datetime
    # empty when every card was already in context
    cards: frozenset[str]

    def line(self) -> str:
        """this mark as one json line, without the newline.

        # Returns

        the line, its cards sorted

        # Example

            >>> Mark(12, dt.datetime(2026, 11, 2, tzinfo=dt.UTC), frozenset({"p2", "p1"})).line()
            '{"at": 12, "ts": "2026-11-02T00:00:00+00:00", "cards": ["p1", "p2"]}'
        """
        return json.dumps({"at": self.at, "ts": self.ts.isoformat(), "cards": sorted(self.cards)})

    @classmethod
    def parse(cls, line: str) -> "Mark | None":
        """read one log line back.

        # Arguments

        * `line` - one line of a ServedLog

        # Returns

        the mark, or None for a line not of this shape; a bool is not an
        offset, although python counts it an int

        # Example

            >>> Mark.parse('{"at": 12, "ts": "2026-11-02T00:00:00Z", "cards": ["p1"]}')
            Mark(at=12, ts=datetime.datetime(2026, 11, 2, 0, 0, tzinfo=datetime.timezone.utc), cards=frozenset({'p1'}))
            >>> Mark.parse('{"at": true, "ts": "2026-11-02", "cards": []}'), Mark.parse("{torn")
            (None, None)
        """
        try:
            # --------------------------------------------------
            # a torn or foreign line is not an error, just not a mark
            # --------------------------------------------------
            stored = json.loads(line)
        except ValueError:
            return None
        # --------------------------------------------------
        # accept only the exact shape, and rebuild the mark from it
        # --------------------------------------------------
        match stored:
            case {"at": int() as at, "ts": str() as stamp, "cards": [*cards]} if not isinstance(at, bool):
                ts = parse_iso(stamp)
                return cls(at, ts, frozenset(nid for nid in cards if isinstance(nid, str))) if ts else None
            case _:
                return None


@dataclass(frozen=True)
class ServedLog:
    """one session's recalls, one Mark per line, only ever appended to.

    a line this short reaches the file in one O_APPEND write, so recalls
    running in parallel in one session each keep their line without a lock

    # Example

        >>> import tempfile
        >>> at = dt.datetime(2026, 11, 2, tzinfo=dt.UTC)
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     log = ServedLog.of("s1", Path(tmp))
        ...     log.marks()
        ...     log.append(Mark(0, at, frozenset({"p1"})))
        ...     log.append(Mark(40, at, frozenset()))
        ...     [mark.at for mark in log.marks()], ServedLog.of("../s1", Path(tmp))
        []
        ([0, 40], None)
    """

    path: Path

    @classmethod
    def of(cls, session: str, directory: Path) -> "ServedLog | None":
        """the log of one session.

        # Arguments

        * `session` - the session id
        * `directory` - where the logs live, `find_served()`

        # Returns

        the log, or None for an id that is not a plain file name
        """
        return cls(directory / f"{session}{LOG_SUFFIX}") if plain_name(session) else None

    def marks(self) -> list[Mark]:
        """every mark in the log, oldest first.

        # Returns

        the marks; [] when the log does not exist, and a malformed line is
        skipped. raises OSError when the log exists and cannot be read
        """
        try:
            # --------------------------------------------------
            # a session that never recalled has no log, which is an empty list
            # --------------------------------------------------
            text = self.path.read_text(encoding=ENCODING, errors="replace")
        except FileNotFoundError:
            return []
        # --------------------------------------------------
        # parse line by line, skipping a malformed one
        # --------------------------------------------------
        return [mark for line in text.splitlines() if (mark := Mark.parse(line)) is not None]

    def append(self, mark: Mark) -> None:
        """add one mark as the log's last line, creating the log and its directory on demand.

        # Arguments

        * `mark` - the recall just made; raises OSError when it cannot be written
        """
        # --------------------------------------------------
        # the first recall of a session creates the directory and the log
        # --------------------------------------------------
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # --------------------------------------------------
        # append one line: one O_APPEND write keeps parallel recalls from interleaving
        # --------------------------------------------------
        with self.path.open("a", encoding=ENCODING) as handle:
            handle.write(mark.line() + "\n")

    @staticmethod
    def held(marks: Sequence[Mark], compactions: Sequence[Record], at: dt.datetime | None = None) -> list[Mark]:
        """the marks still in the session's context at an instant.

        a mark made before `at` is held unless a compaction starts at or past
        its byte and before `at`. a compaction line with no stamp counts as
        before `at`: the conservative reading, which can drop a mark but never
        keep one a compaction erased

        # Arguments

        * `marks` - one session's marks
        * `compactions` - the session's compacting lines, `Transcript.compactions`
        * `at` - the instant to ask about; None is now, where only bytes are compared

        # Returns

        the held marks, in the given order

        # Example

            >>> day = lambda n: dt.datetime(2026, 11, n, tzinfo=dt.UTC)
            >>> marks = [Mark(0, day(1), frozenset({"p1"})), Mark(50, day(3), frozenset({"p2"}))]
            >>> compactions = [Record(30, {"timestamp": "2026-11-02T00:00:00Z"}, "s1")]
            >>> [mark.at for mark in ServedLog.held(marks, compactions)]
            [50]
            >>> [mark.at for mark in ServedLog.held(marks, compactions, day(2))]
            [0]
            >>> [mark.at for mark in ServedLog.held(marks, [Record(30, {}, "s1")], day(4))]
            [50]
        """
        # --------------------------------------------------
        # the compactions that happened before the instant asked about
        # --------------------------------------------------
        erasing = [record.start for record in compactions
                   if at is None or (instant := record.instant) is None or instant < at]
        # --------------------------------------------------
        # a mark is held if made before the instant and no erasing compaction starts at or past its byte
        # --------------------------------------------------
        return [mark for mark in marks
                if (at is None or mark.ts < at) and not any(start >= mark.at for start in erasing)]

    @staticmethod
    def since(directory: Path) -> dt.datetime | None:
        """when recording began on this machine: the oldest first mark of any log.

        a log that cannot be read is left out, which can only move the answer
        later and so report more turns as not recorded

        # Arguments

        * `directory` - where the logs live, `find_served()`

        # Returns

        the oldest first mark's instant, or None when no log holds a mark

        # Example

            >>> import tempfile
            >>> day = lambda n: dt.datetime(2026, 11, n, tzinfo=dt.UTC)
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     ServedLog.since(Path(tmp))
            ...     for session, n in (("s1", 3), ("s2", 1), ("s1", 2)):
            ...         ServedLog.of(session, Path(tmp)).append(Mark(0, day(n), frozenset()))
            ...     ServedLog.since(Path(tmp)) == day(1)
            True
        """
        # --------------------------------------------------
        # collect each log's oldest mark
        # --------------------------------------------------
        firsts: list[dt.datetime] = []
        for path in directory.glob(f"*{LOG_SUFFIX}"):
            try:
                firsts.extend(mark.ts for mark in ServedLog(path).marks()[:1])
            except OSError:
                continue
        # --------------------------------------------------
        # recording began at the earliest of those
        # --------------------------------------------------
        return min(firsts, default=None)
