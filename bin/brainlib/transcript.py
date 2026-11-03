"""brainlib.transcript: what a coding agent's session transcript is, owned once.

where each harness keeps its transcripts, how one is opened (live or gzipped in
the brain's archive), and what each of its lines says. the readers - the
extractor, recall's session record, the misses report - ask these types rather
than parse a harness's directories or line shapes themselves. text in his slot
passes through as written: the wrapper tags a harness injects there are
b-extract's RE_MACHINE to strip, so a third harness is a subclass, an entry
in `Harnesses.discover`, and any wrapper of its own added to that pattern

Author: aav
"""
# this module alone in bin/ walks raw transcript json, whose shape no schema
# describes - a content block is whatever the harness wrote that day. the
# Unknown-type family is suppressed HERE and nowhere else, so the rest of the
# tools keep it (P34: the records are untrusted input, hence the isinstance
# guards below rather than a trusted shape)
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.paths import XdgLayout, plain_name
from brainlib.text import parse_iso
from brainlib.vocab import ENCODING, Env

# --------------------------------------------------
# external
# --------------------------------------------------
import datetime as dt
import glob
import gzip
import io
import json
import re
import zlib
from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Any, ClassVar, Self, final, override

# --------------------------------------------------
# constants
# --------------------------------------------------
# the suffix of an archived copy: the live file's name with this appended
GZIP_SUFFIX = ".gz"
# the uuid every session id ends in, and how much of it a report prints
UUID_LENGTH = 36
SHORT_ID = 8


class TranscriptError(Exception):
    """a transcript that could not be opened or read to its end.

    the one failure every transcript reader catches: the opener raises it from
    the OSError, EOFError and zlib.error a missing, torn or corrupt file throws,
    and its message names the file
    """


@dataclass(frozen=True)
class Place:
    """one directory a harness keeps transcripts in, and the file pattern a session matches.

    listing and lookup read the one (root, pattern) pair, so they cannot
    disagree about how deep a directory's sessions sit
    """

    root: Path
    # `{}` is the session id, e.g. `*/{}.jsonl`
    pattern: str

    def every(self) -> list[Path]:
        """every session file in this place.

        # Returns

        the files, sorted; a missing root holds none
        """
        return sorted(self.root.glob(self.pattern.format("*")))

    def named(self, session: str) -> Path | None:
        """the file of one session.

        # Arguments

        * `session` - the session id, escaped before it reaches the pattern

        # Returns

        the first match, or None for no match or an id that is not a file name

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     place = Place(Path(tmp), "**/{}.jsonl")
            ...     (place.root / "2026").mkdir()
            ...     (place.root / "2026" / "r-1.jsonl").touch()
            ...     place.named("r-1") == place.root / "2026" / "r-1.jsonl", place.named("r-2"), place.named("..")
            (True, None, None)
        """
        if not plain_name(session):
            return None
        return min(self.root.glob(self.pattern.format(glob.escape(session))), default=None)


@dataclass(frozen=True)
class Record:
    """one parsed line of a transcript."""

    # the byte the line starts at, in the decompressed stream
    start: int
    data: dict[str, Any]
    # the session the line belongs to: the harness's own field, else the file stem
    session: str

    @property
    def stamp(self) -> str:
        """the iso-8601 `timestamp` both harnesses write on a line.

        # Returns

        the stamp, empty when the line carries none

        # Example

            >>> Record(0, {"timestamp": "2026-10-31T17:22:44Z"}, "s").stamp
            '2026-10-31T17:22:44Z'
            >>> Record(0, {}, "s").stamp
            ''
        """
        return str(self.data.get("timestamp") or "")

    @property
    def instant(self) -> dt.datetime | None:
        """the stamp, parsed.

        # Returns

        the instant, or None when the line carries no readable stamp

        # Example

            >>> Record(0, {"timestamp": "2026-10-31T17:22:44Z"}, "s").instant.year
            2026
            >>> Record(0, {}, "s").instant is None
            True
        """
        return parse_iso(self.stamp)


@dataclass(frozen=True)
class Driven:
    """who drove the session: a program (True) or him (False)."""

    machine: bool


@dataclass(frozen=True)
class Spoke:
    """text in his slot of a line the harness did not mark as its own; wrapper tags inside it are kept."""

    text: str


@dataclass(frozen=True)
class Replied:
    """the agent's visible text."""

    text: str


@dataclass(frozen=True)
class Interrupted:
    """he cut the agent off."""


@dataclass(frozen=True)
class Denied:
    """a permission prompt he refused."""

    note: str


@dataclass(frozen=True)
class Compacted:
    """this line replaces everything before it with a summary."""


# what one transcript line says; a line can say several
type Event = Driven | Spoke | Replied | Interrupted | Denied | Compacted


@dataclass(frozen=True)
class Transcript:
    """one session's transcript file, read only as far as a question needs.

    one json object per line, gzipped when it is the archived copy. a question
    passes needles, so a line is parsed only when its raw bytes carry one
    """

    path: Path
    harness: "Harness"

    @property
    def stem(self) -> str:
        """the file name minus `.jsonl` / `.jsonl.gz`: the session id the file holds.

        # Returns

        the stem

        # Example

            >>> [Transcript(Path(name), None).stem for name in ("a/s-1.jsonl.gz", "a/s-1.jsonl")]
            ['s-1', 's-1']
        """
        return self.path.name.split(".jsonl")[0]

    def records(self, offset: int = 0, needles: tuple[bytes, ...] = ()) -> Iterator[Record]:
        r"""every json-object line from a byte offset on.

        each line is decoded with replacement before parsing, so a stray byte
        costs that character, never the line

        # Arguments

        * `offset` - the byte of the decompressed stream to start at
        * `needles` - when given, only lines whose raw bytes carry one are parsed

        # Returns

        each line as a Record; a torn last line or a line that is not a json
        object is skipped. raises TranscriptError when the file cannot be read

        # Example

            >>> import tempfile
            >>> claude = Claude(Path("/nonexistent"), Path("/nonexistent"))
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     path = Path(tmp) / "s1.jsonl.gz"
            ...     with gzip.open(path, "wb") as stream:
            ...         _ = stream.write(b'{"sessionId": "s0"}\n[1]\n{"x": 1}\n{"torn')
            ...     [(record.start, record.session) for record in Transcript(path, claude).records()]
            ...     Transcript(path, claude).end()
            [(0, 's0'), (24, 's1')]
            39
        """
        with self._stream() as stream:
            # --------------------------------------------------
            # resume at the byte offset, counting bytes as lines pass
            # --------------------------------------------------
            stream.seek(offset)
            position = offset
            for line in stream:
                start, position = position, position + len(line)
                # --------------------------------------------------
                # skip a line without a needle before paying to parse it
                # --------------------------------------------------
                if needles and not any(needle in line for needle in needles):
                    continue
                try:
                    # --------------------------------------------------
                    # a torn or oversized line is skipped, not fatal
                    # --------------------------------------------------
                    data = json.loads(line.decode(ENCODING, errors="replace"))
                except (ValueError, RecursionError):
                    continue
                # --------------------------------------------------
                # only an object is a record
                # --------------------------------------------------
                if isinstance(data, dict):
                    yield Record(start, data, str(data.get(self.harness.SESSION_FIELD) or "") or self.stem)

    def end(self) -> int:
        """the decompressed length: where the next line will start.

        # Returns

        the length in the stream `records` seeks; raises TranscriptError when
        the file cannot be read to its end
        """
        with self._stream() as stream:
            return stream.seek(0, io.SEEK_END)

    def compactions(self, offset: int = 0) -> list[Record]:
        r"""every compacting line at or past a byte offset.

        a compaction replaces everything before it with a summary, so text
        printed before its start is out of context from its instant on

        # Arguments

        * `offset` - the byte to scan from; nothing before it is read

        # Returns

        the compacting lines, oldest first; each carries its start and its
        stamp. raises TranscriptError when the file cannot be read

        # Example

            >>> import tempfile
            >>> lines = ['{"type":"user","message":{"content":"go"}}', '{"type":"compacted","payload":{}}']
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     path = Path(tmp) / "rollout-1.jsonl"
            ...     _ = path.write_text("\n".join(lines) + "\n")
            ...     log = Transcript(path, Codex(Path(tmp), Path(tmp)))
            ...     [record.start for record in log.compactions()], log.compactions(len(lines[0]) + 2)
            ([43], [])
        """
        # --------------------------------------------------
        # the lines carrying a compaction needle that the harness confirms are compactions
        # --------------------------------------------------
        return [record for record in self.records(offset, self.harness.NEEDLES)
                if any(isinstance(event, Compacted) for event in self.harness.events(record.data))]

    @contextmanager
    def _stream(self) -> Generator[io.BufferedIOBase]:
        """the file opened for binary reading, gunzipped when it is an archived copy.

        the one place a transcript's low-level failures are caught

        # Returns

        the open stream; raises TranscriptError for any failure while it is open
        """
        try:
            # --------------------------------------------------
            # an archived copy is gzip, a live one is plain bytes; either read failing is the transcript's error
            # --------------------------------------------------
            with gzip.open(self.path) if self.path.suffix == GZIP_SUFFIX else self.path.open("rb") as stream:
                yield stream
        except (OSError, EOFError, zlib.error) as broken:
            raise TranscriptError(f"transcript {self.path} unreadable ({broken})") from broken


@dataclass(frozen=True)
class Harness(ABC):
    """one coding agent's transcripts: where it keeps them and what its lines mean."""

    # the user's home, under which the harness writes
    home: Path
    # the brain's cold store root, `XdgLayout.archive`
    archive: Path

    # the evidence rows' `src`, and the harness's folder in the archive
    NAME: ClassVar[str]
    # (directory under home, pattern) per place the harness writes live transcripts
    LIVE: ClassVar[tuple[tuple[str, str], ...]]
    # the pattern inside `<archive>/<NAME>`
    COLD: ClassVar[str]
    # the raw bytes any compacting line carries one of
    NEEDLES: ClassVar[tuple[bytes, ...]]
    # the field a line names its session in; empty when only the file name does
    SESSION_FIELD: ClassVar[str] = ""
    # the variable the harness exports its session id in to the processes it runs; None when it exports none
    SESSION_ENV: ClassVar[Env | None] = None

    @classmethod
    def discover(cls) -> Self:
        """the harness under this user's home and the brain's archive.

        # Returns

        the harness over `Path.home()` and `XdgLayout.archive`
        """
        return cls(Path.home(), XdgLayout.discover().archive)

    def running(self) -> str | None:
        """this process's session id, when it runs under this harness.

        a subagent's environment is its parent's, the session id included, so
        the id names the session, never one agent's context within it

        # Returns

        the id, or None outside the harness or for a harness that exports no id

        # Example

            >>> import os
            >>> saved = os.environ.pop(Env.SESSION_ID, None)
            >>> claude = Claude(Path("/h"), Path("/a"))
            >>> claude.running()
            >>> os.environ[Env.SESSION_ID] = "00000000-0000-4000-8000-000000000001"
            >>> claude.running(), Codex(Path("/h"), Path("/a")).running()
            ('00000000-0000-4000-8000-000000000001', None)
            >>> _ = os.environ.pop(Env.SESSION_ID) if saved is None else os.environ.__setitem__(Env.SESSION_ID, saved)
        """
        return None if self.SESSION_ENV is None else self.SESSION_ENV.read() or None

    @property
    def live(self) -> tuple[Place, ...]:
        """the places the harness writes, and prunes, its transcripts.

        # Returns

        one Place per LIVE entry, in order
        """
        return tuple(Place(self.home / directory, pattern) for directory, pattern in self.LIVE)

    @property
    def cold(self) -> Place:
        """the gzipped copies `b-extract --archive` keeps.

        # Returns

        the Place `<archive>/<NAME>`
        """
        return Place(self.archive / self.NAME, self.COLD)

    def sessions(self) -> Iterator[Transcript]:
        """every live transcript, place by place.

        # Returns

        each transcript, sorted within its place
        """
        return (Transcript(path, self) for place in self.live for path in place.every())

    def archived(self) -> Iterator[Transcript]:
        """every archived copy.

        # Returns

        each gzipped transcript, sorted
        """
        return (Transcript(path, self) for path in self.cold.every())

    def find(self, session: str) -> Transcript | None:
        """one session's transcript, live before archived.

        a live transcript is preferred because an archived copy of a session
        still running stops where the archive pass found it

        # Arguments

        * `session` - the session id

        # Returns

        the transcript, or None when no copy of it survives

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     codex = Codex(Path(tmp), Path(tmp) / "archive")
            ...     cold = codex.cold.root / "2026" / "rollout-1.jsonl.gz"
            ...     cold.parent.mkdir(parents=True)
            ...     cold.touch()
            ...     codex.find("rollout-1") == Transcript(cold, codex), codex.find("rollout-2")
            (True, None)
        """
        # --------------------------------------------------
        # live places first, then the archive
        # --------------------------------------------------
        places = (*self.live, self.cold)
        # --------------------------------------------------
        # the first place that holds the session
        # --------------------------------------------------
        hit = next((path for place in places if (path := place.named(session)) is not None), None)
        return Transcript(hit, self) if hit is not None else None

    def cold_copy(self, path: Path) -> Path:
        """where the archiver keeps a live transcript: its place's layout mirrored, gzipped.

        mirrored rather than flattened, because a claude project folder IS the
        transcript's `proj` label

        # Arguments

        * `path` - a live transcript, inside one of the LIVE places

        # Returns

        the archived copy's path; raises ValueError for a path outside every live place

        # Example

            >>> Claude(Path("/h"), Path("/a")).cold_copy(Path("/h/.claude/projects/-p/s1.jsonl"))
            PosixPath('/a/claude/-p/s1.jsonl.gz')
        """
        # --------------------------------------------------
        # the live place the path sits under
        # --------------------------------------------------
        root = next((place.root for place in self.live if path.is_relative_to(place.root)), None)
        # --------------------------------------------------
        # a path outside every live place has no cold counterpart
        # --------------------------------------------------
        if root is None:
            raise ValueError(f"{path} is not in any of {self.NAME}'s live places")
        # --------------------------------------------------
        # mirror the live layout under the archive, gzip-suffixed
        # --------------------------------------------------
        relative = path.relative_to(root)
        return self.cold.root / relative.with_name(relative.name + GZIP_SUFFIX)

    @abstractmethod
    def project(self, path: Path) -> str:
        """the `proj` label of a live transcript.

        # Arguments

        * `path` - the transcript

        # Returns

        a short readable label
        """

    @staticmethod
    def short(session: str) -> str:
        """a session id cut to what a report row prints: its trailing uuid's first block.

        # Arguments

        * `session` - the full id, a uuid or `rollout-<stamp>-<uuid>`

        # Returns

        8 characters, enough to find the transcript

        # Example

            >>> Harness.short("rollout-2026-06-07T12-20-15-019ea2e2-86f1-7da1-afa4-2199e7fb876b")
            '019ea2e2'
        """
        return session[-UUID_LENGTH:][:SHORT_ID]

    @staticmethod
    def texts(blocks: Iterable[object], separator: str, kind: str | None = None) -> str:
        """the `text` of a line's content blocks, joined.

        a block is untrusted json, so one that is not an object, or whose
        `text` is not a string, contributes nothing

        # Arguments

        * `blocks` - the content list
        * `separator` - what goes between two blocks' text
        * `kind` - when given, only blocks whose `type` is this

        # Returns

        the joined text; a block with no `text` adds an empty piece

        # Example

            >>> Harness.texts([{"type": "text", "text": "a"}, {"text": 1}, "b", {"type": "image"}], "|", "text")
            'a'
            >>> Harness.texts([{"text": "a"}, {}], "|")
            'a|'
        """
        return separator.join(text for block in blocks if isinstance(block, dict)
                              and (kind is None or block.get("type") == kind)
                              and isinstance(text := block.get("text", ""), str))

    @abstractmethod
    def events(self, data: dict[str, Any]) -> Iterator[Event]:
        """what one line says, in the order a reader must act on it.

        # Arguments

        * `data` - one parsed line

        # Returns

        each event the line carries; a line about none of them yields nothing
        """


@final
@dataclass(frozen=True)
class Claude(Harness):
    """claude code: one folder per project, one file per session."""

    NAME = "claude"
    # the non-recursive pattern is what leaves out `<session>/subagents/`: a
    # subagent's user turns are dispatch prompts, not his words
    LIVE = ((".claude/projects", "*/{}.jsonl"),)
    COLD = "*/{}.jsonl.gz"
    SESSION_FIELD = "sessionId"
    SESSION_ENV = Env.SESSION_ID
    # the flag claude sets on the line that replaces a compacted conversation
    COMPACT_FLAG = "isCompactSummary"
    # the words that line opens with, which a transcript carries without the flag too
    COMPACT_OPENING = "This session is being continued from a previous conversation"
    NEEDLES = (COMPACT_FLAG.encode(), COMPACT_OPENING.encode())
    # what claude writes into his slot when he cuts a turn off
    INTERRUPT_MARK = "[Request interrupted by user"
    # the most characters of a project folder's name a `proj` label keeps
    PROJECT_LABEL = 28
    # what claude writes into a tool_result when he refuses a permission prompt
    DENIAL = re.compile(
        r"(doesn't want to (proceed|take this action)|user (rejected|doesn't want|has interrupted)|"
        r"rejected the|user chose not)", re.IGNORECASE)

    @override
    def project(self, path: Path) -> str:
        """the project folder's name, with the home and repos prefixes stripped.

        # Arguments

        * `path` - the transcript, whose folder is its working directory with `/` spelled `-`

        # Returns

        at most 28 characters of the stripped name, or the whole name when nothing is left

        # Example

            >>> Claude(Path("/srv/u"), Path("/a")).project(Path("/x/-srv-u-repos-personal-site/s1.jsonl"))
            'site'
        """
        # --------------------------------------------------
        # the project folder is the home-prefixed path with its separators flattened to hyphens
        # --------------------------------------------------
        name, home = path.parent.name, str(self.home).replace("/", "-")
        return (name.replace(f"{home}-repos-personal-", "")
                    .replace(f"{home}-repos-", "")
                    .replace(f"{home}-", "")[:self.PROJECT_LABEL]) or name

    @override
    def events(self, data: dict[str, Any]) -> Iterator[Event]:
        """a claude line's events.

        a user line's `entrypoint` says who drove the session (`sdk-*` is a
        program). an assistant line yields its visible text. a user
        line yields each refused permission, then an interruption or his words,
        unless the harness wrote them (`isMeta`, a compaction summary)

        # Arguments

        * `data` - one parsed line

        # Returns

        the line's events

        # Example

            >>> claude = Claude(Path("/h"), Path("/a"))
            >>> list(claude.events({"type": "user", "entrypoint": "cli", "message": {"content": "hi"}}))
            [Driven(machine=False), Spoke(text='hi')]
            >>> list(claude.events({"type": "user", "isCompactSummary": True, "message": {"content": "x"}}))
            [Compacted()]
        """
        # --------------------------------------------------
        # read the line's type and its message
        # --------------------------------------------------
        kind, message = data.get("type"), data.get("message")
        # --------------------------------------------------
        # a user line that names an entrypoint says whether a machine drove the session
        # --------------------------------------------------
        if kind == "user" and data.get("entrypoint"):
            yield Driven(str(data["entrypoint"]).startswith("sdk"))
        # --------------------------------------------------
        # the content is a string or a list of blocks
        # --------------------------------------------------
        content = message.get("content") if isinstance(message, dict) else None
        # --------------------------------------------------
        # a compaction is the flagged line, or the user line that opens with the continuation words
        # --------------------------------------------------
        compacted = data.get(self.COMPACT_FLAG) is True or (
            kind == "user" and isinstance(content, str) and content.startswith(self.COMPACT_OPENING))
        if compacted:
            yield Compacted()
        # --------------------------------------------------
        # the typed blocks, ignoring anything that is not an object
        # --------------------------------------------------
        blocks = [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []
        # --------------------------------------------------
        # an assistant line replies with its text blocks, a user line speaks
        # --------------------------------------------------
        if kind == "assistant" and isinstance(message, dict):
            if (text := self.texts(blocks, " ", "text")).strip():
                yield Replied(text)
        elif kind == "user" and isinstance(message, dict):
            yield from self._user(content, blocks, spoken=not (data.get("isMeta") or compacted))

    def _user(self, content: object, blocks: list[dict[str, Any]], *, spoken: bool) -> Iterator[Event]:
        """a user line's refused permissions, then his interruption or his words.

        # Arguments

        * `content` - the message's content: his text, or a list of blocks
        * `blocks` - that list's blocks, empty for text
        * `spoken` - False when the harness wrote the line, so its text is not his

        # Returns

        a Denied per refusing tool_result, then Interrupted on the mark, else
        Spoke when allowed; nothing for a line with no text
        """
        for block in blocks:
            # --------------------------------------------------
            # a tool_result that carries a refusal is a denial
            # --------------------------------------------------
            note = block.get("content", "") if block.get("type") == "tool_result" else None
            if isinstance(note, list):
                note = self.texts(note, " ")
            if isinstance(note, str) and self.DENIAL.search(note):
                yield Denied(note)
        # --------------------------------------------------
        # the typed text, from a bare string or the text blocks
        # --------------------------------------------------
        text = content if isinstance(content, str) else self.texts(blocks, "\n", "text")
        if not text.strip():
            return
        # --------------------------------------------------
        # an interrupt marker is not speech; anything else is the user's words unless meta or compacted
        # --------------------------------------------------
        if self.INTERRUPT_MARK in text:
            yield Interrupted()
        elif spoken:
            yield Spoke(text)


@final
@dataclass(frozen=True)
class Codex(Harness):
    """codex: rollout files in date folders, live and archived alike."""

    NAME = "codex"
    LIVE = ((".codex/sessions", "**/{}.jsonl"), (".codex/archived_sessions", "**/{}.jsonl"))
    COLD = "**/{}.jsonl.gz"
    NEEDLES = (b'"type":"compacted"',)

    @override
    def project(self, path: Path) -> str:
        """codex keeps no project folder, so every transcript is labelled by the harness.

        # Arguments

        * `path` - the transcript

        # Returns

        NAME
        """
        return self.NAME

    @override
    def events(self, data: dict[str, Any]) -> Iterator[Event]:
        """a codex line's events.

        `session_meta` says who drove the session (`exec` or a subagent is a
        program); an aborted turn is an interruption; a message is the agent's
        text or his

        # Arguments

        * `data` - one parsed line

        # Returns

        the line's events

        # Example

            >>> codex = Codex(Path("/h"), Path("/a"))
            >>> list(codex.events({"type": "session_meta", "payload": {"source": "exec"}}))
            [Driven(machine=True)]
            >>> list(codex.events({"type": "response_item", "payload": {"type": "turn_aborted"}}))
            [Interrupted()]
        """
        # --------------------------------------------------
        # the payload is an object, else empty
        # --------------------------------------------------
        payload = data.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        content = payload.get("content")
        # --------------------------------------------------
        # dispatch on the line type, the payload type and its role
        # --------------------------------------------------
        match data.get("type"), payload.get("type"), payload.get("role"):
            case "session_meta", _, _:
                source = payload.get("source")
                yield Driven(source == "exec" or (isinstance(source, dict) and "subagent" in source))
            case "compacted", _, _:
                yield Compacted()
            case _, "turn_aborted" | "task_aborted", _:
                yield Interrupted()
            case _, "message", "assistant" if isinstance(content, list):
                if (text := self.texts(content, " ")).strip():
                    yield Replied(text)
            case _, "message", "user" if isinstance(content, list):
                if text := self.texts(content, "\n").strip():
                    yield Spoke(text)
            case _:
                pass


@dataclass(frozen=True)
class Harnesses:
    """every harness whose transcripts the brain reads, in a fixed order."""

    all: tuple[Harness, ...]

    @classmethod
    def discover(cls, archive: Path | None = None) -> "Harnesses":
        """every known harness, under this user's home: THE registry.

        # Arguments

        * `archive` - the cold store root; `XdgLayout.archive` when omitted

        # Returns

        claude then codex, the order their sessions are listed in
        """
        home, cold = Path.home(), archive or XdgLayout.discover().archive
        return cls((Claude(home, cold), Codex(home, cold)))

    def named(self, name: str) -> Harness | None:
        """the harness an evidence row's `src` names.

        # Arguments

        * `name` - the row's `src`

        # Returns

        the harness, or None for a name no harness has

        # Example

            >>> harnesses = Harnesses.discover(Path("/a"))
            >>> harnesses.named("codex") == Codex(Path.home(), Path("/a")), harnesses.named("")
            (True, None)
        """
        return next((harness for harness in self.all if name == harness.NAME), None)

    def running(self) -> tuple[Harness, str] | None:
        """the harness this process runs under, and its session id.

        # Returns

        the first harness whose `running` names a session, with that id; None
        when none does
        """
        return next(((harness, session) for harness in self.all if (session := harness.running()) is not None), None)

    def sessions(self) -> Iterator[Transcript]:
        """every harness's live transcripts.

        # Returns

        each transcript, harness by harness
        """
        return chain.from_iterable(harness.sessions() for harness in self.all)

    def archived(self) -> Iterator[Transcript]:
        """every harness's archived copies.

        # Returns

        each gzipped transcript, harness by harness
        """
        return chain.from_iterable(harness.archived() for harness in self.all)
