"""brainlib.session: what a tool printed in full each session, owned once.

each call a tool records appends one Mark to its session's SessionLog, and
a reader reads the logs back: the record of a run comes from the one process that knows
it ran, never from a guess at a shell command's text. each tool's logs live in
their own dir (`XdgLayout.session_log`), outside every repo. a SessionRecord
reads one session's log back, minus what a compaction erased

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.paths import XdgLayout, plain_name
from brainlib.text import parse_iso
from brainlib.transcript import Harness, Record, TranscriptError
from brainlib.vocab import ENCODING

# --------------------------------------------------
# external
# --------------------------------------------------
import datetime as dt
import errno
import json
import os
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Self

# --------------------------------------------------
# constants
# --------------------------------------------------
# a session's log file: the session id, then this
LOG_SUFFIX = ".jsonl"


@dataclass(frozen=True)
class Mark:
    """one call in a session: where its output starts, when it ran, which ids it printed in full."""

    # the transcript's end when the call started: its output lies past this byte
    at: int
    # utc
    ts: dt.datetime
    # the ids the call printed in full; empty when every one was already in context
    items: frozenset[str]

    def line(self) -> str:
        """this mark as one json line, without the newline.

        # Returns

        the line, its items sorted

        # Example

            >>> Mark(12, dt.datetime(2026, 11, 2, tzinfo=dt.UTC), frozenset({"p2", "p1"})).line()
            '{"at": 12, "ts": "2026-11-02T00:00:00+00:00", "items": ["p1", "p2"]}'
        """
        return json.dumps({"at": self.at, "ts": self.ts.isoformat(), "items": sorted(self.items)})

    @classmethod
    def parse(cls, line: str) -> Self | None:
        """read one log line back.

        # Arguments

        * `line` - one line of a SessionLog

        # Returns

        the mark, or None for a line not of this shape; a bool is not an
        offset, although python counts it an int. a line keying its ids
        `cards` reads the same as one keying them `items`

        # Example

            >>> Mark.parse('{"at": 12, "ts": "2026-11-02T00:00:00Z", "items": ["p1"]}')
            Mark(at=12, ts=datetime.datetime(2026, 11, 2, 0, 0, tzinfo=datetime.timezone.utc), items=frozenset({'p1'}))
            >>> Mark.parse('{"at": 12, "ts": "2026-11-02T00:00:00Z", "cards": ["p1"]}').items
            frozenset({'p1'})
            >>> Mark.parse('{"at": true, "ts": "2026-11-02", "items": []}'), Mark.parse("{torn")
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
            case ({"at": int() as at, "ts": str() as stamp, "items": [*items]}
                  | {"at": int() as at, "ts": str() as stamp, "cards": [*items]}) if not isinstance(at, bool):
                ts = parse_iso(stamp)
                return cls(at, ts, frozenset(nid for nid in items if isinstance(nid, str))) if ts else None
            case _:
                return None

    def held(self, compactions: Sequence[Record], instant: dt.datetime | None = None) -> bool:
        """whether this mark is still in the session's context at an instant.

        a mark made before `instant` is held unless a compaction starts at or
        past its byte and before `instant`. a compaction line with no stamp
        counts as before `instant`: the conservative reading, which can drop a
        mark but never keep one a compaction erased

        # Arguments

        * `compactions` - the session's compacting lines, `Transcript.compactions`
        * `instant` - the instant to ask about; None is now, where only bytes are compared

        # Returns

        True when the mark is held

        # Example

            >>> day = lambda n: dt.datetime(2026, 11, n, tzinfo=dt.UTC)
            >>> marks = [Mark(0, day(1), frozenset({"p1"})), Mark(50, day(3), frozenset({"p2"}))]
            >>> compactions = [Record(30, {"timestamp": "2026-11-02T00:00:00Z"}, "s1")]
            >>> [mark.at for mark in marks if mark.held(compactions)]
            [50]
            >>> [mark.at for mark in marks if mark.held(compactions, day(2))]
            [0]
            >>> [mark.at for mark in marks if mark.held([Record(30, {}, "s1")], day(4))]
            [50]
        """
        # --------------------------------------------------
        # made after the instant asked about, it is not yet in context
        # --------------------------------------------------
        if instant is not None and self.ts >= instant:
            return False
        # --------------------------------------------------
        # erased by a compaction that happened before the instant and starts at or past its byte
        # --------------------------------------------------
        return not any(record.start >= self.at for record in compactions
                       if instant is None or (stamp := record.instant) is None or stamp < instant)


@dataclass(frozen=True)
class SessionLog:
    """one session's calls of one tool, one Mark per line, only ever appended to.

    each line reaches the file in one `os.write` on an O_APPEND descriptor,
    so calls running in parallel in one session each keep their line without
    a lock

    # Example

        >>> import tempfile
        >>> at = dt.datetime(2026, 11, 2, tzinfo=dt.UTC)
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     log = SessionLog.of("s1", Path(tmp))
        ...     log.read()
        ...     log.append(Mark(0, at, frozenset({"p1"})))
        ...     log.append(Mark(40, at, frozenset()))
        ...     [mark.at for mark in log.read()], log.first().at, SessionLog.of("../s1", Path(tmp))
        []
        ([0, 40], 0, None)
    """

    path: Path

    @classmethod
    def of(cls, session: str, directory: Path) -> Self | None:
        """the log of one session.

        # Arguments

        * `session` - the session id
        * `directory` - the tool's log dir, `XdgLayout.session_log`

        # Returns

        the log, or None for an id that is not a plain file name
        """
        return cls(directory / f"{session}{LOG_SUFFIX}") if plain_name(session) else None

    def read(self) -> list[Mark]:
        """every mark in the log, oldest first.

        # Returns

        the marks; [] when the log does not exist, and a malformed line is skipped

        # Raises

        OSError when the log exists and cannot be read
        """
        try:
            # --------------------------------------------------
            # a session that never called the tool has no log, which is an empty list
            # --------------------------------------------------
            text = self.path.read_text(encoding=ENCODING, errors="replace")
        except FileNotFoundError:
            return []
        # --------------------------------------------------
        # parse line by line, skipping a malformed one
        # --------------------------------------------------
        return [mark for line in text.splitlines() if (mark := Mark.parse(line)) is not None]

    def first(self) -> Mark | None:
        """the log's oldest mark, read no further than the line that holds it.

        # Returns

        the first well-formed mark; None when the log does not exist or holds none

        # Raises

        OSError when the log exists and cannot be read
        """
        try:
            with self.path.open(encoding=ENCODING, errors="replace") as lines:
                return next((mark for line in lines if (mark := Mark.parse(line)) is not None), None)
        except FileNotFoundError:
            return None

    def append(self, mark: Mark) -> None:
        """add one mark as the log's last line, creating the log and its directory on demand.

        # Arguments

        * `mark` - the call just made

        # Raises

        OSError when the log cannot be written, or took only part of the line
        """
        # --------------------------------------------------
        # the first call of a session creates the directory and the log
        # --------------------------------------------------
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # --------------------------------------------------
        # append one line in one write: O_APPEND keeps parallel calls from interleaving
        # --------------------------------------------------
        line = f"{mark.line()}\n".encode(ENCODING)
        handle = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o666)
        try:
            written = os.write(handle, line)
        finally:
            os.close(handle)
        # --------------------------------------------------
        # a second write would not be atomic with the first, so a short one is reported, not finished
        # --------------------------------------------------
        if written != len(line):
            raise OSError(errno.EIO, f"wrote {written} of {len(line)} bytes", str(self.path))

    @classmethod
    def since(cls, directory: Path) -> dt.datetime | None:
        """when recording began in this log dir: the oldest first mark of any log.

        a log that cannot be read is left out, which can only move the answer
        later and so report more turns as not recorded

        # Arguments

        * `directory` - one tool's log dir, `XdgLayout.session_log`

        # Returns

        the oldest first mark's instant, or None when no log holds a mark

        # Example

            >>> import tempfile
            >>> day = lambda n: dt.datetime(2026, 11, n, tzinfo=dt.UTC)
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     SessionLog.since(Path(tmp))
            ...     for session, n in (("s1", 3), ("s2", 1), ("s1", 2)):
            ...         SessionLog.of(session, Path(tmp)).append(Mark(0, day(n), frozenset()))
            ...     SessionLog.since(Path(tmp)) == day(1)
            True
        """
        # --------------------------------------------------
        # collect each log's oldest mark
        # --------------------------------------------------
        firsts: list[dt.datetime] = []
        for path in directory.glob(f"*{LOG_SUFFIX}"):
            try:
                first = cls(path).first()
            except OSError:
                continue
            if first is not None:
                firsts.append(first.ts)
        # --------------------------------------------------
        # recording began at the earliest of those
        # --------------------------------------------------
        return min(firsts, default=None)


@dataclass(frozen=True)
class SessionRecord:
    """what one session has been shown in full by one tool, so each item prints once.

    read from the session's SessionLog, which each tool appends to by its own
    rule. a later call in the same session prints `earlier` in place of an
    item instead of reprinting it. with no session id nothing is remembered
    and every call prints in full. a mark a compaction erased is not held
    (`Mark.held`). the record is a cache - an unreadable or unwritable
    log costs a repeated item, never a crash

    # Example

        >>> import tempfile
        >>> from brainlib import Claude
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     running, xdg = (Claude(Path(tmp), Path(tmp)), "s1"), XdgLayout(Path(tmp))
        ...     first, parallel = (SessionRecord.load("b-recall", running, xdg) for _ in range(2))
        ...     first.mark(["p1"])
        ...     parallel.mark(["p3"])
        ...     after = SessionRecord.load("b-recall", running, xdg)
        ...     unkeyed = SessionRecord.load("b-recall", None, xdg)
        ...     [after.seen(nid) for nid in ("p1", "p2", "p3")], unkeyed.seen("p1")
        ([True, False, True], False)
    """

    # what a later call prints in place of an item this session was shown in full
    EARLIER: ClassVar[str] = "printed in full earlier this session"

    # the calling tool's command, which names its log dir and opens each stderr message
    tool: str
    # the session's log; None with no session id
    log: SessionLog | None = None
    # the marks this session still holds in context
    marks: tuple[Mark, ...] = ()
    # the transcript's end as this call starts, stamped on the mark it makes
    at: int = 0

    @classmethod
    def load(cls, tool: str, running: tuple[Harness, str] | None, xdg: XdgLayout) -> Self:
        r"""read one session's record, minus every mark a compaction has erased.

        # Arguments

        * `tool` - the calling tool's command, which names its log dir and opens each stderr message
        * `running` - the harness and session this call runs in, `Harnesses.running()`
        * `xdg` - the data root holding the tool's log dir, `XdgLayout.discover()`

        # Returns

        the session's record; unkeyed with no session id or for an id that
        is not a plain file name. with no readable transcript every mark is
        kept, since there is no evidence of a compaction to act on

        # Example

            >>> import tempfile
            >>> from brainlib import Claude
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     running, xdg = (Claude(Path(tmp), Path(tmp)), "s1"), XdgLayout(Path(tmp))
            ...     log = Path(tmp) / ".claude" / "projects" / "p" / "s1.jsonl"
            ...     log.parent.mkdir(parents=True)
            ...     _ = log.write_text('{"type": "user"}\n')
            ...     SessionRecord.load("b-recall", running, xdg).mark(["p1"])
            ...     kept = SessionRecord.load("b-recall", running, xdg).seen("p1")
            ...     with log.open("a") as appended:
            ...         _ = appended.write('{"type": "user", "isCompactSummary": true}\n')
            ...     kept, SessionRecord.load("b-recall", running, xdg).seen("p1")
            (True, False)
        """
        # --------------------------------------------------
        # no session, or one whose id is no file name, remembers nothing
        # --------------------------------------------------
        if running is None or (log := SessionLog.of(running[1], xdg.session_log(tool))) is None:
            return cls(tool)
        harness, session = running
        # --------------------------------------------------
        # read the marks; an unreadable log holds none
        # --------------------------------------------------
        try:
            marks = log.read()
        except OSError as broken:
            print(f"{tool}: session log unreadable ({broken}); everything prints in full", file=sys.stderr)
            marks = []
        # --------------------------------------------------
        # drop the marks a compaction erased, read off the session's transcript
        # --------------------------------------------------
        if (transcript := harness.find(session)) is None:
            return cls(tool, log, tuple(marks))
        try:
            at = transcript.end()
            compactions = transcript.compactions(min(mark.at for mark in marks)) if marks else []
        except TranscriptError as broken:
            # no transcript is no evidence: every mark is kept, and this one
            # stamped at the start so the next call scans the whole session
            print(f"{tool}: {broken}; keeping the session record", file=sys.stderr)
            return cls(tool, log, tuple(marks))
        return cls(tool, log, tuple(mark for mark in marks if mark.held(compactions)), at)

    def seen(self, item: str) -> bool:
        """whether this session has already been shown an item in full.

        # Arguments

        * `item` - the id to check

        # Returns

        True when an earlier call in this session printed it
        """
        return any(item in mark.items for mark in self.marks)

    def mark(self, items: Iterable[str]) -> None:
        """append this call to the session's log, with the items it printed in full.

        a write that fails is reported on stderr and otherwise ignored: the
        cost is those items printing in full again on the next call

        # Arguments

        * `items` - the ids just printed in full
        """
        if self.log is None:
            return
        try:
            self.log.append(Mark(self.at, dt.datetime.now(dt.UTC), frozenset(items)))
        except OSError as broken:
            print(f"{self.tool}: session log {self.log.path} not saved ({broken})", file=sys.stderr)

    @classmethod
    def earlier(cls, reread: str) -> str:
        """the line a later call prints in place of an item: EARLIER, then how to bring the item back.

        a subagent shares its parent's session id but not its context, so the
        line tells it how to get the text when it does not hold it

        # Arguments

        * `reread` - the command or read that brings the item back

        # Returns

        the line

        # Example

            >>> SessionRecord.earlier("read p2.md")
            'printed in full earlier this session; if it is not in your context: read p2.md'
        """
        return f"{cls.EARLIER}; if it is not in your context: {reread}"
