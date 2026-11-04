#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-open-items: write, stamp, answer and watch open-item files, with life's todos kept in step.

an open item is one file, `plans/open-items/<ID>-<slug>.md` (P66). his answer goes
under its `## Your call` heading, and its last line is a footer holding the sha256
of everything above it. the agent writes the item and stamps it; he edits it, or
answers its todo on the board and life rewrites the section; a hash that no longer
matches is how the agent knows, without asking, which item carries his answer.
when `life` is on PATH, each command that changes what the board shows runs
`life open-item` first

    stamp ITEM...  `life open-item ask`, then the footer; prints the watch command when no watch holds the folder
    status [DIR]   each item as edited | unchanged | new (DIR defaults to plans/open-items)
    answer ITEM    replaces `## Your call` with stdin; refuses an item that does not exist
    new PATH       makes an unstamped item at PATH from stdin
    resolve ITEM   `life open-item resolve`, then deletes the item, only if that succeeded
    park ITEM      `life open-item park`; with no todo, writes `Parked.` as the section
    unpark ITEM    `life open-item unpark`; with no todo, empties a `Parked.` section
    watch [-d DIR]... [-e SECONDS]
                   polls each DIR (plans/open-items) every SECONDS (30), prints each new or edited
                   item that is not parked, once per content, with its note, then exits

life's status 5 says no todo backs the item, which leaves it the brain's alone;
any other failure leaves the item as it was. every write holds the folder's write
lock, a flock on the folder itself, which life's ask holds too, so no lock is held
across a `life` call. watch holds a lock of its own, under
$XDG_RUNTIME_DIR/brain-open-items/, beside what it has reported

Author: aav
"""
# brainlib lives in the brain's bin/, three folders up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "bin"))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import ENCODING, Args, Env, Exit, Flag, Json, NoVerdict, Tool, UsageError, read_text, write_text

# --------------------------------------------------
# external
# --------------------------------------------------
import fcntl
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import time
from collections.abc import Generator, Iterator, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Self

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages
TOOL = Path(__file__).stem
# the folder a command reads when it names none
DEFAULT_DIR = Path("plans/open-items")
# an item file, matched in its folder
ITEM_GLOB = "*.md"
# the footer line; an html comment so it does not render
FOOTER = "<!-- sha256: {} -->"
# matched anywhere, so an answer typed below the footer still reads as an edit
FOOTER_RE = re.compile(r"^<!-- sha256: ([0-9a-f]{64}) -->[ \t]*$", re.MULTILINE)
# the heading of the section his answer goes in
HEADING = "## Your call"
HEADING_RE = re.compile(rf"^{re.escape(HEADING)}[ \t]*$", re.MULTILINE)
# a parked item's whole section, the line life's projection writes for a todo in backlog
PARKED = "Parked."
# the blank line between the question, the heading, the section and the footer
GAP = "\n\n"
# how a note's lines are set under their item in watch's report
NOTE_INDENT = "  "
# how often watch looks, in seconds, when -e names nothing
EVERY = 30.0
# the folder under $XDG_RUNTIME_DIR holding each watched folder's lock and what watch reported from it
RUNTIME = "brain-open-items"
# a stamp's probe holds a folder's watch lock for an instant; a watch that finds it held waits this
# long, once, before it takes the lock for another watch's
GRACE = 0.1
# life's command; it is on PATH or the brain works without it (R-OI-2)
LIFE = "life"
# life's status for an item no todo backs, its Exit.NOT_FOUND
NO_TODO = 5


class Command(StrEnum):
    """the subcommands, each the first positional."""

    STAMP = "stamp"
    STATUS = "status"
    ANSWER = "answer"
    NEW = "new"
    RESOLVE = "resolve"
    PARK = "park"
    UNPARK = "unpark"
    WATCH = "watch"

    @classmethod
    def parse(cls, words: Sequence[str]) -> tuple[Self, list[str]]:
        """the subcommand the first word names, and the arguments after it.

        # Arguments

        * `words` - the positionals, the subcommand first

        # Returns

        the subcommand and its arguments

        # Raises

        UsageError for an unknown subcommand or a wrong count of arguments

        # Example

            >>> Command.parse(["status"])
            (<Command.STATUS: 'status'>, [])
        """
        word, *rest = words
        try:
            command = cls(word)
        except ValueError:
            raise UsageError(f"unknown command {word!r}") from None
        least, most = command.arity
        if len(rest) < least or (most is not None and len(rest) > most):
            span = f"{least}" if least == most else f"{least} to {'any' if most is None else most}"
            raise UsageError(f"{command} takes {span} argument(s), not {len(rest)}")
        return command, rest

    @property
    def arity(self) -> tuple[int, int | None]:
        """how many arguments follow the subcommand.

        # Returns

        (least, most); most None is no upper bound

        # Example

            >>> Command.STAMP.arity, Command.STATUS.arity, Command.ANSWER.arity
            ((1, None), (0, 1), (1, 1))
        """
        match self:
            case Command.STAMP:
                return 1, None
            case Command.STATUS:
                return 0, 1
            case Command.WATCH:
                return 0, 0
            case _:
                return 1, 1


class Status(StrEnum):
    """where an item stands against its footer."""

    # stamped, and changed since
    EDITED = "edited"
    # stamped, and as stamped
    UNCHANGED = "unchanged"
    # no footer yet: an item life made, or one the agent has not stamped
    NEW = "new"


class LifeAction(StrEnum):
    """the `life open-item` actions this tool runs."""

    ASK = "ask"
    RESOLVE = "resolve"
    PARK = "park"
    UNPARK = "unpark"


class Reply(Enum):
    """what a `life open-item` call came to."""

    # life did it: the todo moved, and life brought the item in step
    DONE = "done"
    # no todo backs the item, or no life is on PATH: the item is the brain's alone
    NO_TODO = "no todo"
    # life refused or failed, and said why on stderr
    REFUSED = "refused"


@dataclass(frozen=True)
class ItemText:
    r"""an open item's text, whole, and what the brain reads off it.

    # Example

        >>> text = ItemText("# Q01: x\n\n## Your call\n\nyes\n")
        >>> text.status, text.note, ItemText(text.stamped()).status
        (<Status.NEW: 'new'>, 'yes', <Status.UNCHANGED: 'unchanged'>)
    """

    # the file's text, as read
    text: str

    @classmethod
    def piped(cls) -> Self:
        """the item text on stdin, verbatim.

        # Returns

        the text

        # Raises

        UsageError when stdin is a terminal, so nothing was piped
        """
        if sys.stdin.isatty():
            raise UsageError("the text goes on stdin: `< file`, or a quoted heredoc")
        return cls(sys.stdin.read())

    @staticmethod
    def digest(body: str) -> str:
        r"""the sha256 a footer holds for a body, trailing whitespace normalised.

        # Arguments

        * `body` - the item text above the footer

        # Returns

        the hex digest

        # Example

            >>> ItemText.digest("a\n") == ItemText.digest("a")
            True
        """
        return hashlib.sha256(body.rstrip().encode(ENCODING)).hexdigest()

    @property
    def body(self) -> str:
        r"""the item without its footer line; text typed below the footer joins the body.

        # Returns

        the body, stripped

        # Example

            >>> ItemText("# Q01: x\n\n<!-- sha256: " + "a" * 64 + " -->\nB\n").body
            '# Q01: x\n\nB'
            >>> ItemText("# Q01: x\n").body
            '# Q01: x'
        """
        if match := FOOTER_RE.search(self.text):
            return (self.text[: match.start()].rstrip() + GAP + self.text[match.end() :].strip()).strip()
        return self.text.rstrip()

    @property
    def status(self) -> Status:
        r"""whether the item changed since it was stamped.

        # Returns

        the status

        # Example

            >>> ItemText("# Q01: x\n\n<!-- sha256: " + "a" * 64 + " -->\n").status
            <Status.EDITED: 'edited'>
        """
        match = FOOTER_RE.search(self.text)
        if match is None:
            return Status.NEW
        return Status.UNCHANGED if match.group(1) == self.digest(self.body) else Status.EDITED

    @property
    def note(self) -> str:
        r"""his answer: what follows the last `## Your call` heading in the body.

        # Returns

        the section, stripped; empty for an item with no heading

        # Example

            >>> ItemText("# Q\n\nsee ## Your call\n\n## Your call\n\nB\n\n<!-- sha256: " + "a" * 64 + " -->\n").note
            'B'
        """
        headings = list(HEADING_RE.finditer(self.body))
        return self.body[headings[-1].end() :].strip() if headings else ""

    @property
    def parked(self) -> bool:
        r"""whether the section reads `Parked.` and nothing else.

        # Returns

        True for a parked item, which watch passes by

        # Example

            >>> ItemText("# Q\n\n## Your call\n\nParked.\n").parked
            True
        """
        return self.note == PARKED

    @property
    def fingerprint(self) -> str:
        """the sha256 of the whole text, which watch reports once.

        # Returns

        the hex digest
        """
        return hashlib.sha256(self.text.encode(ENCODING)).hexdigest()

    def stamped(self) -> str:
        r"""the item with a footer matching its body.

        # Returns

        the whole item: the body, a blank line, the footer

        # Example

            >>> ItemText("# Q\n").stamped() == "# Q\n\n" + FOOTER.format(ItemText.digest("# Q")) + "\n"
            True
        """
        body = self.body
        return f"{body}{GAP}{FOOTER.format(self.digest(body))}\n"

    def answered(self, section: str) -> str:
        r"""the item with its `## Your call` section replaced whole.

        everything through the last heading above the footer, and the footer
        with all below it, are kept byte for byte, so a heading quoted in the
        question never counts

        # Arguments

        * `section` - the new section; empty for an empty section

        # Returns

        the whole item; one with no heading gets one after a blank line

        # Example

            >>> footer = "<!-- sha256: " + "a" * 64 + " -->\n"
            >>> ItemText("# Q\n\n## Your call\n\nold\n\n" + footer).answered("new") == (
            ...     "# Q\n\n## Your call\n\nnew\n\n" + footer)
            True
            >>> ItemText("# Q\n\n## Your call\n\nold\n\n" + footer).answered("") == "# Q\n\n## Your call\n\n" + footer
            True
            >>> ItemText("# Q\n").answered("Parked.")
            '# Q\n\n## Your call\n\nParked.\n'
        """
        # --------------------------------------------------
        # the footer, and what is above it
        # --------------------------------------------------
        footer = FOOTER_RE.search(self.text)
        above, tail = (self.text[: footer.start()], self.text[footer.start() :]) if footer else (self.text, "")
        # --------------------------------------------------
        # everything through the last heading, as written; a missing heading is added
        # --------------------------------------------------
        headings = list(HEADING_RE.finditer(above))
        kept = above[: headings[-1].end()] if headings else above.rstrip() + GAP + HEADING
        # --------------------------------------------------
        # a stamped item: the section between blank lines, then the footer as written
        # --------------------------------------------------
        if tail:
            return kept + GAP + (section + GAP if section else "") + tail
        # --------------------------------------------------
        # an unstamped item ends with its section
        # --------------------------------------------------
        return kept + "\n" + (f"\n{section}\n" if section else "")

    def unstamped(self) -> str:
        r"""the item with no footer, and with a `## Your call` heading.

        # Returns

        the whole item, as `new` writes it

        # Example

            >>> ItemText("# Q\n\n<!-- sha256: " + "a" * 64 + " -->\n").unstamped()
            '# Q\n\n## Your call\n'
        """
        bare = ItemText(self.body)
        return bare.answered(bare.note)


@dataclass(frozen=True)
class Folder:
    """one open-items folder."""

    # the folder, as named on the command line or as an item's parent
    path: Path

    @property
    def items(self) -> list[Path]:
        """every item in the folder.

        # Returns

        the item files, sorted
        """
        return sorted(path for path in self.path.glob(ITEM_GLOB) if path.is_file())

    def status(self) -> None:
        """print each item's status, edited first: the ones carrying his answer.

        # Raises

        UsageError when the folder does not exist
        """
        if not self.path.is_dir():
            raise UsageError(f"no open-items dir at {self.path}")
        for status, name in sorted((ItemText(read_text(path)).status, path.name) for path in self.items):
            print(f"{status:<10} {name}")

    @property
    def key(self) -> str:
        """the name its watch lock and its reports go under: the folder's real path, hashed.

        # Returns

        the hex digest of the resolved path
        """
        return hashlib.sha256(str(self.path.resolve()).encode(ENCODING)).hexdigest()

    @contextmanager
    def locked(self) -> Generator[None]:
        """the folder's write lock: a flock on the folder itself, which no write replaces.

        life's ask holds the same lock, so an item is never written by both at
        once, and an `answer` checks the item under it, so one that lands after
        a resolve's delete finds nothing to write

        # Raises

        NoVerdict when the folder cannot be opened
        """
        try:
            handle = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY)
        except OSError as error:
            raise NoVerdict(f"{self.path} cannot be locked: {error.strerror}") from None
        try:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield
        finally:
            os.close(handle)


@dataclass(frozen=True)
class Life:
    """the `life` command, when it is on PATH."""

    # its path, or None when the brain works without it
    command: str | None

    @classmethod
    def discover(cls) -> Self:
        """the `life` on PATH, if any.

        # Returns

        the command
        """
        return cls(shutil.which(LIFE))

    def open_item(self, action: LifeAction, item: Path) -> Reply:
        """run `life open-item <action> <item>`, its output passed through.

        # Arguments

        * `action` - what life does to the item's todo
        * `item` - the item

        # Returns

        what the call came to; NO_TODO, without a call, when no life is on PATH
        """
        if self.command is None:
            return Reply.NO_TODO
        # fixed arguments, the item a path, and no shell (S603)
        status = subprocess.run([self.command, "open-item", action, str(item.absolute())],  # noqa: S603
                                check=False).returncode
        if status == 0:
            return Reply.DONE
        return Reply.NO_TODO if status == NO_TODO else Reply.REFUSED


@dataclass(frozen=True)
class Item:
    """one open-item file, and every command that writes it."""

    # the item, as named on the command line
    path: Path

    @property
    def folder(self) -> Folder:
        """the folder holding it.

        # Returns

        the folder
        """
        return Folder(self.path.parent)

    def read(self) -> ItemText:
        """the item's text.

        # Returns

        the text

        # Raises

        NoVerdict when there is no item
        """
        try:
            return ItemText(read_text(self.path))
        except FileNotFoundError:
            raise NoVerdict(f"no item at {self.path}") from None

    def present(self) -> None:
        """refuse an item that does not exist.

        # Raises

        NoVerdict when there is no item
        """
        if not self.path.is_file():
            raise NoVerdict(f"no item at {self.path}")

    def stamp(self, life: Life) -> None:
        """ask life for the item's todo, then write the footer.

        life reconciles the item before it returns, so the footer covers the
        section it wrote, and watch does not wake on the agent's own question.
        the stamp lands whatever life replied: catch-up asks again for a
        stamped item with no todo

        # Arguments

        * `life` - the life to ask

        # Raises

        NoVerdict when there is no item, or its folder cannot be locked
        """
        self.present()
        life.open_item(LifeAction.ASK, self.path)
        with self.folder.locked():
            write_text(self.path, self.read().stamped())
        print(f"stamped {self.path}")

    @staticmethod
    def stamp_all(items: Sequence["Item"], life: Life) -> None:
        """stamp each item, then print the command that starts a watch over the folders no watch holds.

        the agent starts the watch, because only a background job of its own can wake it (R-W-5)

        # Arguments

        * `items` - the items
        * `life` - the life to ask

        # Raises

        NoVerdict as `stamp` raises it
        """
        for item in items:
            item.stamp(life)
        watch = Watch.discover()
        folders = list(dict.fromkeys(item.folder for item in items))
        if unwatched := [folder for folder in folders if watch is None or not watch.held(folder)]:
            print(f"no watch: {Watch.command(unwatched)}")

    def answer(self, section: str) -> None:
        """replace the item's `## Your call` section, writing nothing when it already reads so.

        # Arguments

        * `section` - the new section

        # Raises

        NoVerdict when there is no item, checked under the folder's lock, or the folder cannot be locked
        """
        with self.folder.locked():
            text = self.read()
            answered = text.answered(section.strip())
            if answered != text.text:
                write_text(self.path, answered)

    def new(self, text: ItemText) -> None:
        """make an unstamped item.

        # Arguments

        * `text` - the item; any footer is dropped and a missing heading added

        # Raises

        NoVerdict when the path is taken, or the folder cannot be made or locked
        """
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise NoVerdict(f"{self.path.parent} cannot be made: {error.strerror}") from None
        with self.folder.locked():
            if self.path.exists():
                raise NoVerdict(f"{self.path} exists")
            write_text(self.path, text.unstamped())
        print(f"new {self.path}")

    def resolve(self, life: Life) -> Exit:
        """move the item's todo on through life, then delete the item, only when that succeeded.

        so life never sees an item gone from a todo still asking

        # Arguments

        * `life` - the life to resolve through

        # Returns

        OK, or FAILED with the item kept when life refused

        # Raises

        NoVerdict when there is no item, or its folder cannot be locked
        """
        self.present()
        if life.open_item(LifeAction.RESOLVE, self.path) is Reply.REFUSED:
            return Exit.FAILED
        with self.folder.locked():
            self.path.unlink(missing_ok=True)
        print(f"resolved {self.path}")
        return Exit.OK

    def park(self, life: Life, *, parked: bool) -> Exit:
        """park the item or unpark it: its todo through life, else its section here.

        # Arguments

        * `life` - the life to park through
        * `parked` - True to park, False to unpark

        # Returns

        OK, or FAILED with the item kept when life refused

        # Raises

        NoVerdict when there is no item, or its folder cannot be locked
        """
        self.present()
        action = LifeAction.PARK if parked else LifeAction.UNPARK
        match life.open_item(action, self.path):
            case Reply.REFUSED:
                return Exit.FAILED
            case Reply.DONE:
                pass
            case Reply.NO_TODO:
                # --------------------------------------------------
                # no todo: the section is the brain's, and unpark empties only a parked one
                # --------------------------------------------------
                with self.folder.locked():
                    text = self.read()
                    if parked or text.parked:
                        answered = text.answered(PARKED if parked else "")
                        if answered != text.text:
                            write_text(self.path, answered)
        print(f"{action}ed {self.path}")
        return Exit.OK


@dataclass(frozen=True)
class Watch:
    """the watch's locks and its reports, one pair per folder, under the runtime root."""

    # $XDG_RUNTIME_DIR/brain-open-items
    root: Path

    @classmethod
    def discover(cls) -> Self | None:
        """the watch's root, under this login's runtime dir.

        # Returns

        the watch, or None when $XDG_RUNTIME_DIR is unset or relative
        """
        runtime = Env.XDG_RUNTIME_DIR.read()
        return cls(Path(runtime) / RUNTIME) if Path(runtime).is_absolute() else None

    @classmethod
    def start(cls, args: Args) -> Exit:
        """a watch over the folders the command line names, run until it reports.

        # Arguments

        * `args` - the command line: each -d a folder, plans/open-items when none; -e the seconds between looks

        # Returns

        as `run`

        # Raises

        UsageError for a folder that does not exist or a bad -e; NoVerdict when
        $XDG_RUNTIME_DIR is unset or relative
        """
        # --------------------------------------------------
        # the folders, each one there
        # --------------------------------------------------
        folders = [Folder(Path(name)) for name in args.values(Flag.DIR)] or [Folder(DEFAULT_DIR)]
        if missing := [folder.path for folder in folders if not folder.path.is_dir()]:
            raise UsageError(f"no open-items dir at {missing[0]}")
        # --------------------------------------------------
        # the seconds between looks, a finite number above 0
        # --------------------------------------------------
        try:
            every = float(args.value(Flag.EVERY, str(EVERY)))
        except ValueError:
            raise UsageError(f"{Flag.EVERY} takes seconds") from None
        if not (math.isfinite(every) and every > 0):
            raise UsageError(f"{Flag.EVERY} takes seconds above 0")
        # --------------------------------------------------
        # somewhere to hold the lock
        # --------------------------------------------------
        watch = cls.discover()
        if watch is None:
            raise NoVerdict(f"${Env.XDG_RUNTIME_DIR} is no absolute path, so a watch has nowhere to hold its lock")
        return watch.run(folders, every)

    @staticmethod
    def command(folders: Sequence[Folder]) -> str:
        """the shell command that starts a watch over these folders.

        # Arguments

        * `folders` - the folders

        # Returns

        `python3 <this script> watch --dir <folder>...`
        """
        dirs = " ".join(f"{Flag.DIR} {shlex.quote(str(folder.path))}" for folder in folders)
        return f"python3 {shlex.quote(__file__)} {Command.WATCH} {dirs}"

    def held(self, folder: Folder) -> bool:
        """whether a watch holds the folder's lock.

        # Arguments

        * `folder` - the folder

        # Returns

        True while a watch runs on it
        """
        lock = self.root / f"{folder.key}.lock"
        if not lock.is_file():
            return False
        handle = os.open(lock, os.O_RDONLY)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        finally:
            os.close(handle)
        return False

    def hold(self, folder: Folder, stack: ExitStack) -> bool:
        """take the folder's lock for as long as the stack stays open.

        a killed watch's lock goes with its process, so it never blocks the next

        # Arguments

        * `folder` - the folder
        * `stack` - closes the lock's handle, and so releases it

        # Returns

        True when this watch holds it, False when another does
        """
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        handle = os.open(self.root / f"{folder.key}.lock", os.O_RDWR | os.O_CREAT, 0o600)
        stack.callback(os.close, handle)
        for wait in (GRACE, None):
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                if wait is not None:
                    time.sleep(wait)
            else:
                return True
        return False

    def reported(self, folder: Folder) -> dict[str, str]:
        """what watch has reported from a folder: each item's name and its fingerprint then.

        # Arguments

        * `folder` - the folder

        # Returns

        the reports; none for a folder never reported, or a record that does not parse
        """
        try:
            record = json.loads(read_text(self.root / f"{folder.key}.json"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        if not Json.is_object(record):
            return {}
        return {name: value for name, value in record.items() if isinstance(value, str)}

    def unreported(self, folder: Folder) -> Iterator[tuple[Path, ItemText]]:
        """every item to report from a folder: new or edited, not parked, and not reported as it reads.

        # Arguments

        * `folder` - the folder

        # Returns

        each item and its text
        """
        reported = self.reported(folder)
        for path in folder.items:
            try:
                text = ItemText(read_text(path))
            except FileNotFoundError:
                continue
            if text.status is not Status.UNCHANGED and not text.parked and reported.get(path.name) != text.fingerprint:
                yield path, text

    def record(self, folder: Folder, found: Sequence[tuple[Path, ItemText]]) -> None:
        """add a folder's reports to its record, and drop the items that are gone.

        # Arguments

        * `folder` - the folder
        * `found` - the items just reported from it
        """
        names = {path.name for path in folder.items}
        kept = {name: value for name, value in self.reported(folder).items() if name in names}
        kept |= {path.name: text.fingerprint for path, text in found}
        write_text(self.root / f"{folder.key}.json", json.dumps(kept, indent=1, sort_keys=True) + "\n")

    def run(self, folders: Sequence[Folder], every: float) -> Exit:
        """hold each folder's lock, then poll until an item is to report; print it, record it, and exit.

        # Arguments

        * `folders` - the folders to watch
        * `every` - seconds between looks

        # Returns

        OK once something was reported, BLOCKED when another watch holds a folder
        """
        with ExitStack() as stack:
            # --------------------------------------------------
            # every folder's lock, or none
            # --------------------------------------------------
            for folder in folders:
                if not self.hold(folder, stack):
                    print(f"{TOOL}: already watching {folder.path}", file=sys.stderr)
                    return Exit.BLOCKED
            # --------------------------------------------------
            # look until something is new
            # --------------------------------------------------
            while not (found := {folder: items for folder in folders if (items := list(self.unreported(folder)))}):
                time.sleep(every)
            # --------------------------------------------------
            # each item with its note, then the record, so a re-run does not repeat it
            # --------------------------------------------------
            for folder, items in found.items():
                for path, text in items:
                    print(f"{text.status} {path}")
                    for line in text.note.splitlines():
                        print(f"{NOTE_INDENT}{line}".rstrip())
                self.record(folder, items)
        return Exit.OK


def main(args: Args) -> Exit | None:
    """dispatch the subcommand.

    # Arguments

    * `args` - the parsed command line; the first positional is the subcommand

    # Returns

    the subcommand's verdict

    # Raises

    UsageError for an unknown subcommand, a wrong count of arguments, a flag
    another subcommand owns, or a bad -e; NoVerdict for an item that does not exist
    """
    # --------------------------------------------------
    # the subcommand, and its arguments; -d and -e are watch's alone
    # --------------------------------------------------
    command, rest = Command.parse(args.positional())
    if command is not Command.WATCH and (args.has(Flag.DIR) or args.has(Flag.EVERY)):
        raise UsageError(f"{Flag.DIR} and {Flag.EVERY} are {Command.WATCH}'s")
    life = Life.discover()
    match command:
        case Command.STAMP:
            Item.stamp_all([Item(Path(name)) for name in rest], life)
        case Command.STATUS:
            Folder(Path(rest[0]) if rest else DEFAULT_DIR).status()
        case Command.ANSWER:
            Item(Path(rest[0])).answer(ItemText.piped().text)
        case Command.NEW:
            Item(Path(rest[0])).new(ItemText.piped())
        case Command.RESOLVE:
            return Item(Path(rest[0])).resolve(life)
        case Command.PARK | Command.UNPARK:
            return Item(Path(rest[0])).park(life, parked=command is Command.PARK)
        case Command.WATCH:
            return Watch.start(args)
    return Exit.OK


if __name__ == "__main__":
    Tool(TOOL, __doc__, (Flag.DIR, Flag.EVERY), positionals=(1, None)).run(main)
