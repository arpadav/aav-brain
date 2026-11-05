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
    status [DIR]   each item as edited | new | parked | unchanged (DIR defaults to plans/open-items)
    question ITEM  prints the item without `## Your call` and without the footer: what it asks
    answer ITEM    replaces `## Your call` with stdin, which may not be empty; refuses an item that does not exist
    clear ITEM     empties `## Your call`, which answer's empty stdin never does; refuses an item that does not exist
    new PATH       makes an unstamped item at PATH from stdin, which may not be empty
    resolve ITEM   `life open-item resolve`, then deletes the item, only if that succeeded
    park ITEM      `life open-item park`; with no todo, ends the section with a `Parked.` paragraph
    unpark ITEM    `life open-item unpark`; with no todo, drops that paragraph
    watch [-d DIR]... [-e SECONDS]
                   polls each DIR (plans/open-items) every SECONDS (30), prints each new or edited
                   item that is not parked, once per content, with its note, then exits

life's status 5 says no todo backs the item, which leaves it the brain's alone,
as does a `life` absent from PATH. any other status, 6 (this machine not set up
for life) among them, a `life` that cannot run and one that does not answer in
time are a refusal: `resolve`, `park` and `unpark` leave the item as it was,
life's stderr or a line of this script's saying why, and `stamp` stamps it all
the same. an item is named to life, and in every line printed here, by its real
path, as `realpath` spells it. every write here holds the folder's write lock, a
flock on the folder itself, which life's ask holds too, so no lock is held
across a `life` call; every other life write lands without it. watch holds a
lock of its own, under $XDG_RUNTIME_DIR/brain-open-items/, beside what it has
reported

Author: aav
"""
# the brain's root is three folders up, and brainlib is in its bin/
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
from collections.abc import Generator, Iterable, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from enum import Enum, StrEnum, auto
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
# a footer-shaped line, matched anywhere; `ItemText.footer` says which one is the footer
FOOTER_RE = re.compile(r"^<!-- sha256: ([0-9a-f]{64}) -->[ \t]*$", re.MULTILINE)
# the heading of the section his answer goes in
HEADING = "## Your call"
HEADING_RE = re.compile(rf"^{re.escape(HEADING)}[ \t]*$", re.MULTILINE)
# the paragraph life's projection ends the section with for a todo in the parked column
PARKED = "Parked."
# a section whose last paragraph is PARKED
PARKED_RE = re.compile(rf"(?:\A|\n[ \t]*\n){re.escape(PARKED)}\Z")
# the blank line between the question, the heading, each paragraph of the section and the footer
GAP = "\n\n"
# the blank lines leading a section and the whitespace trailing it; a first line's indentation is kept
EDGES_RE = re.compile(r"\A(?:[ \t]*\n)+|\s+\Z")
# how a note's lines are set under their item in watch's report
NOTE_INDENT = "  "
# how often watch looks, in seconds, when -e names nothing
EVERY = 30.0
# the folder under $XDG_RUNTIME_DIR holding each watched folder's lock and what watch reported from it
RUNTIME = "brain-open-items"
# a watch's lock file and its record, each named by its folder's real path, hashed
LOCK = ".lock"
RECORD = ".json"
# a watch that finds its lock held tries once more after this many seconds, the holder maybe a
# stamp's probe, which lets go at once
GRACE = 0.1
# life's command; when it is not on PATH the brain works without it
LIFE = "life"
# life's status when it did what it was asked
LIFE_DONE = 0
# life's status for an item no todo backs
LIFE_NO_TODO = 5
# a `life open-item` call unanswered after this many seconds is hung: its longest, `ask` on a todo moving
# between plan steps, makes 9 `todo` calls (whoami, columns, the lookup, 2 untags, 2 tags, the ask, the
# host's check), each given 60 s by life, and one minute more covers life's own work: (9 + 1) * 60
LIFE_TIMEOUT = (9 + 1) * 60.0
# why a watch cannot run, for watch's refusal and stamp's note
NO_RUNTIME = f"${Env.XDG_RUNTIME_DIR} is no absolute path, so a watch has nowhere to hold its lock"
# a missing item, and a missing folder
NO_ITEM = "no item at {}"
NO_DIR = "no open-items dir at {}"


class Command(StrEnum):
    """the subcommands, each the first positional."""

    STAMP = "stamp"
    STATUS = "status"
    QUESTION = "question"
    ANSWER = "answer"
    CLEAR = "clear"
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
    """where an item stands, declared in the order `status` lists them: the two that wake a watch first."""

    # stamped, and changed since
    EDITED = "edited"
    # no footer yet: an item life or `new` made, or one the agent has not stamped
    NEW = "new"
    # its section ends with a `Parked.` paragraph, whatever its footer says, so an edited item parked reads so
    PARKED = "parked"
    # stamped, and as stamped
    UNCHANGED = "unchanged"

    @property
    def wakes(self) -> bool:
        """whether an item standing so wakes a watch.

        # Returns

        True for a new or an edited item

        # Example

            >>> [status.wakes for status in Status]
            [True, True, False, False]
        """
        return self in (Status.EDITED, Status.NEW)

    @property
    def rank(self) -> int:
        """where `status` lists an item standing so.

        # Returns

        the declaration index
        """
        return list(Status).index(self)


class LifeAction(StrEnum):
    """the `life open-item` actions this tool runs."""

    ASK = "ask"
    RESOLVE = "resolve"
    PARK = "park"
    UNPARK = "unpark"

    @property
    def past(self) -> str:
        """the action done, as a line printed after it names it.

        # Returns

        the past tense

        # Example

            >>> [action.past for action in LifeAction]
            ['asked', 'resolved', 'parked', 'unparked']
        """
        match self:
            case LifeAction.ASK:
                return "asked"
            case LifeAction.RESOLVE:
                return "resolved"
            case LifeAction.PARK:
                return "parked"
            case LifeAction.UNPARK:
                return "unparked"


class Reply(Enum):
    """what a `life open-item` call came to."""

    # life did it: the todo moved, and life brought the item in step
    DONE = auto()
    # no todo backs the item, or no life is on PATH: the item is the brain's alone
    NO_TODO = auto()
    # life refused or failed, saying why on stderr, or it could not run or did not answer, which this script says
    REFUSED = auto()

    @classmethod
    def of(cls, status: int) -> "Reply":
        """what life's exit status says.

        # Arguments

        * `status` - the status

        # Returns

        the reply

        # Example

            >>> [Reply.of(status).name for status in (0, 4, 5, 6)]
            ['DONE', 'REFUSED', 'NO_TODO', 'REFUSED']
        """
        if status == LIFE_DONE:
            return cls.DONE
        return cls.NO_TODO if status == LIFE_NO_TODO else cls.REFUSED


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

    @staticmethod
    def trimmed(section: str) -> str:
        r"""a section without the blank lines leading it or the whitespace trailing it.

        # Arguments

        * `section` - the section

        # Returns

        the section, its first line's indentation kept

        # Example

            >>> ItemText.trimmed("\n \n  - a\n- b \n\n")
            '  - a\n- b'
        """
        return EDGES_RE.sub("", section)

    @property
    def footer(self) -> re.Match[str] | None:
        r"""the footer: the last footer-shaped line below the first `## Your call` heading, or in an item with none.

        one above every heading is quoted in the question, and is never the
        footer; a heading typed below the footer leaves it the footer

        # Returns

        the footer's match, None for an unstamped item

        # Example

            >>> line = "<!-- sha256: " + "a" * 64 + " -->"
            >>> ItemText(f"# Q: {line}\n\n{line}\n\n## Your call\n").footer is None
            True
            >>> ItemText(f"# Q\n\n## Your call\n\n{line}\n## Your call\nyes\n").footer is not None
            True
        """
        first = HEADING_RE.search(self.text)
        footers = list(FOOTER_RE.finditer(self.text, first.end() if first else 0))
        return footers[-1] if footers else None

    @property
    def body(self) -> str:
        r"""the item without its footer line; text typed below the footer joins the body.

        # Returns

        the body, stripped

        # Example

            >>> ItemText("# Q01: x\n\n<!-- sha256: " + "a" * 64 + " -->\nB\n").body
            '# Q01: x\n\nB'
            >>> ItemText("\n# Q01: x\n").body
            '# Q01: x'
        """
        if footer := self.footer:
            return (self.text[: footer.start()].rstrip() + GAP + self.text[footer.end() :].strip()).strip()
        return self.text.strip()

    @property
    def status(self) -> Status:
        r"""where the item stands: parked, else against its footer.

        # Returns

        the status

        # Example

            >>> ItemText("# Q01: x\n\n<!-- sha256: " + "a" * 64 + " -->\n").status
            <Status.EDITED: 'edited'>
        """
        if self.parked:
            return Status.PARKED
        if self.footer is None:
            return Status.NEW
        return Status.UNCHANGED if self.sealed else Status.EDITED

    @property
    def sealed(self) -> bool:
        r"""whether the item has a footer and reads as stamped, parked or not.

        # Returns

        True when the footer holds the body's sha256

        # Example

            >>> ItemText(ItemText("# Q\n\n## Your call\n\nParked.\n").stamped()).sealed
            True
        """
        return (footer := self.footer) is not None and footer.group(1) == self.digest(self.body)

    @property
    def heading(self) -> re.Match[str] | None:
        r"""the heading opening the section: the body's last `## Your call` line, so one quoted above it never counts.

        # Returns

        the heading's match in `body`, None for an item with no heading

        # Example

            >>> text = ItemText("# Q: see\n## Your call\n\n## Your call\n\nyes\n")
            >>> text.body[text.heading.start() :]
            '## Your call\n\nyes'
        """
        headings = list(HEADING_RE.finditer(self.body))
        return headings[-1] if headings else None

    @property
    def question(self) -> str:
        r"""what the item asks: the body above its section's heading.

        # Returns

        the question, stripped; the whole body for an item with no heading

        # Example

            >>> ItemText("# Q01: x\n\nwhy\n\n## Your call\n\nyes\n\n<!-- sha256: " + "a" * 64 + " -->\n").question
            '# Q01: x\n\nwhy'
            >>> ItemText("# Q01: x\n").question
            '# Q01: x'
        """
        heading = self.heading
        return self.body[: heading.start()].strip() if heading else self.body

    @property
    def note(self) -> str:
        r"""his answer: what follows the last `## Your call` heading in the body.

        # Returns

        the section, trimmed; empty for an item with no heading

        # Example

            >>> ItemText("# Q\n\nsee ## Your call\n\n## Your call\n\nB\n\n<!-- sha256: " + "a" * 64 + " -->\n").note
            'B'
        """
        heading = self.heading
        return self.trimmed(self.body[heading.end() :]) if heading else ""

    @property
    def parked(self) -> bool:
        r"""whether the section's last paragraph is `Parked.`.

        # Returns

        True for a parked item, which watch passes by

        # Example

            >>> ItemText("# Q\n\n## Your call\n\n2026-11-03 14:02 arpad: later\n\nParked.\n").parked
            True
            >>> ItemText("# Q\n\n## Your call\n\nnot Parked.\n").parked
            False
        """
        return PARKED_RE.search(self.note) is not None

    @property
    def fingerprint(self) -> str:
        """the sha256 of the whole text, which watch reports once.

        # Returns

        the hex digest
        """
        return hashlib.sha256(self.text.encode(ENCODING)).hexdigest()

    def parked_note(self) -> str:
        r"""the note, ending with a `Parked.` paragraph.

        # Returns

        the note as it reads when parked already, else with the paragraph added

        # Example

            >>> ItemText("# Q\n\n## Your call\n\nyes\n").parked_note()
            'yes\n\nParked.'
            >>> ItemText("# Q\n\n## Your call\n").parked_note()
            'Parked.'
        """
        return self.note if self.parked else GAP.join(filter(None, (self.note, PARKED)))

    def unparked_note(self) -> str:
        r"""the note without its closing `Parked.` paragraph.

        # Returns

        the note, every paragraph above that one kept

        # Example

            >>> ItemText("# Q\n\n## Your call\n\nyes\n\nParked.\n").unparked_note()
            'yes'
        """
        match = PARKED_RE.search(self.note)
        return self.note[: match.start()] if match else self.note

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

        everything through the last heading is kept, its leading blank lines
        aside, so a heading quoted in the question never counts. text typed
        below the footer is part of the section, and goes with it; the footer
        line is kept, so a stamped item whose section changes reads edited
        after, or parked when the new section ends with `Parked.`

        # Arguments

        * `section` - the new section; empty for an empty section

        # Returns

        the whole item; one with no heading gets one after a blank line

        # Example

            >>> footer = "<!-- sha256: " + "a" * 64 + " -->"
            >>> ItemText(f"# Q\n\n## Your call\n\nold\n\n{footer}\ntyped below\n").answered("new") == (
            ...     f"# Q\n\n## Your call\n\nnew\n\n{footer}\n")
            True
            >>> ItemText(f"# Q\n\n## Your call\n\nold\n\n{footer}\n").answered("") == (
            ...     f"# Q\n\n## Your call\n\n{footer}\n")
            True
            >>> ItemText("# Q\n").answered("Parked.")
            '# Q\n\n## Your call\n\nParked.\n'
        """
        # --------------------------------------------------
        # the body through its last heading, as written; a missing heading is added
        # --------------------------------------------------
        body, heading = self.body, self.heading
        kept = body[: heading.end()] if heading else body + GAP + HEADING
        # --------------------------------------------------
        # a stamped item: the section between blank lines, then the footer line
        # --------------------------------------------------
        if footer := self.footer:
            return kept + GAP + (section + GAP if section else "") + footer.group(0) + "\n"
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

    # the folder's real path
    path: Path

    @classmethod
    def of(cls, path: Path) -> Self:
        """the folder a path names.

        # Arguments

        * `path` - the path, relative or absolute

        # Returns

        the folder, by its real path
        """
        return cls(path.resolve())

    @classmethod
    def distinct(cls, paths: Iterable[Path]) -> list[Self]:
        """the folders these paths name, each once, by its real path.

        # Arguments

        * `paths` - the paths, relative or absolute

        # Returns

        one folder per real path, in first-named order
        """
        return list(dict.fromkeys(map(cls.of, paths)))

    def items(self) -> list[Path]:
        """every item in the folder.

        # Returns

        the item files, sorted
        """
        return sorted(path.resolve() for path in self.path.glob(ITEM_GLOB) if path.is_file())

    def status(self) -> None:
        """print each item's status, the ones carrying his input first.

        # Raises

        NoVerdict when the folder does not exist, or an item cannot be read
        """
        if not self.path.is_dir():
            raise NoVerdict(NO_DIR.format(self.path))
        width = max(map(len, Status))
        rows = sorted(((Item(path).read().status, path.name) for path in self.items()),
                      key=lambda row: (row[0].rank, row[1]))
        for status, name in rows:
            print(f"{status:<{width}} {name}")

    @contextmanager
    def locked(self) -> Generator[None]:
        """the folder's write lock: a flock on the folder itself, which no write replaces.

        every write here holds it, and life's `open-item ask` holds it for its
        whole run, so those two never write an item at once. every other life
        write lands without it, so a write here can still land between its
        read and its write. an `answer` checks the item under it, so one that
        lands after a resolve's delete finds nothing to write

        # Raises

        NoVerdict when the folder does not exist or cannot be opened
        """
        try:
            handle = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY)
        except FileNotFoundError:
            raise NoVerdict(NO_DIR.format(self.path)) from None
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
        * `item` - the item's real path

        # Returns

        what the call came to; NO_TODO, without a call, when no life is on PATH; REFUSED, with one
        line on stderr, when life cannot run or does not answer within LIFE_TIMEOUT
        """
        if self.command is None:
            return Reply.NO_TODO
        argv = [self.command, "open-item", action, str(item)]
        try:
            # fixed arguments, the item a path, and no shell (S603)
            done = subprocess.run(argv, check=False, timeout=LIFE_TIMEOUT)  # noqa: S603
        except subprocess.TimeoutExpired:
            print(f"{TOOL}: `{LIFE} open-item {action}` gave no answer in {LIFE_TIMEOUT:g} s", file=sys.stderr)
            return Reply.REFUSED
        except OSError as error:
            print(f"{TOOL}: {self.command} cannot run: {error.strerror}", file=sys.stderr)
            return Reply.REFUSED
        return Reply.of(done.returncode)


@dataclass(frozen=True)
class Item:
    """one open-item file, and every command that writes it."""

    # the item's real path
    path: Path

    @classmethod
    def of(cls, path: Path) -> Self:
        """the item a path names.

        # Arguments

        * `path` - the path, relative or absolute, as named on the command line

        # Returns

        the item, by its real path, as `realpath` spells it
        """
        return cls(path.resolve())

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

        NoVerdict when there is no item, or it cannot be read or decoded
        """
        try:
            return ItemText(read_text(self.path))
        except FileNotFoundError:
            raise NoVerdict(NO_ITEM.format(self.path)) from None
        except OSError as error:
            raise NoVerdict(f"{self.path} cannot be read: {error.strerror}") from None
        except UnicodeDecodeError as error:
            raise NoVerdict(f"{self.path} cannot be read: {error.reason} at byte {error.start}") from None

    def present(self) -> None:
        """refuse an item that does not exist.

        # Raises

        NoVerdict when there is no item
        """
        if not self.path.is_file():
            raise NoVerdict(NO_ITEM.format(self.path))

    def write(self, text: ItemText, section: str) -> None:
        """write the item with this section, unless its note already reads so.

        # Arguments

        * `text` - the item as read under the folder's lock
        * `section` - the new section, trimmed
        """
        if section != text.note:
            write_text(self.path, text.answered(section))

    def stamp(self, life: Life) -> None:
        """ask life for the item's todo, then write the footer, unless it already matches.

        life reconciles the item before it returns, so the footer covers the
        section it wrote, and watch does not wake on the agent's own question.
        the stamp lands whatever life replied: catch-up asks again for a
        stamped item with no todo. the folder's lock cannot be held across
        the life call, which takes it itself, so an edit of his landing
        between life's return and the lock is stamped with the rest, and
        never reported

        # Arguments

        * `life` - the life to ask

        # Raises

        NoVerdict when there is no item, it cannot be read, or its folder cannot be locked; life is asked
        before any of these but the first
        """
        life.open_item(LifeAction.ASK, self.path)
        with self.folder.locked():
            text = self.read()
            if (stamped := text.stamped()) != text.text:
                write_text(self.path, stamped)
        print(f"stamped {self.path}")

    @staticmethod
    def stamp_all(items: Sequence["Item"], life: Life) -> None:
        """stamp each item, once all of them exist, then say how a watch starts over the folders of those stamped.

        # Arguments

        * `items` - the items
        * `life` - the life to ask

        # Raises

        NoVerdict when an item does not exist, before any is stamped, or as `stamp` raises it, after the
        ones stamped before it are advised on
        """
        for item in items:
            item.present()
        stamped: list[Item] = []
        try:
            for item in items:
                item.stamp(life)
                stamped.append(item)
        finally:
            if stamped:
                Watch.advise(list(dict.fromkeys(item.folder for item in stamped)))

    def answer(self, section: str) -> None:
        """replace the item's `## Your call` section, writing nothing when it already reads so.

        # Arguments

        * `section` - the new section; its leading blank lines and trailing whitespace are dropped

        # Raises

        NoVerdict when there is no item, checked again under the folder's lock, or the folder cannot be locked
        """
        self.present()
        with self.folder.locked():
            self.write(self.read(), ItemText.trimmed(section))

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
        print(f"{LifeAction.RESOLVE.past} {self.path}")
        return Exit.OK

    def park(self, life: Life, action: LifeAction) -> Exit:
        """park the item or unpark it: its todo through life, else its section here.

        with no todo, park ends the section with a `Parked.` paragraph and
        unpark drops only that paragraph, so his answer above it stays. an
        item stamped while parked is stamped again once unparked, so the
        watch never wakes on the agent's own unpark

        # Arguments

        * `life` - the life to park through
        * `action` - PARK or UNPARK

        # Returns

        OK, or FAILED with the item kept when life refused

        # Raises

        NoVerdict when there is no item, or its folder cannot be locked
        """
        self.present()
        match life.open_item(action, self.path):
            case Reply.REFUSED:
                return Exit.FAILED
            case Reply.DONE:
                pass
            case Reply.NO_TODO:
                with self.folder.locked():
                    text = self.read()
                    if action is LifeAction.PARK:
                        self.write(text, text.parked_note())
                    elif text.parked:
                        unparked = ItemText(text.answered(text.unparked_note()))
                        write_text(self.path, unparked.stamped() if text.sealed else unparked.text)
        print(f"{action.past} {self.path}")
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

        UsageError for a bad -e; NoVerdict for a folder that does not exist, or
        when $XDG_RUNTIME_DIR is unset or relative
        """
        # --------------------------------------------------
        # the folders, each once and each there
        # --------------------------------------------------
        folders = Folder.distinct([Path(name) for name in args.values(Flag.DIR)] or [DEFAULT_DIR])
        if missing := [folder.path for folder in folders if not folder.path.is_dir()]:
            raise NoVerdict(NO_DIR.format(missing[0]))
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
            raise NoVerdict(NO_RUNTIME)
        return watch.run(folders, every)

    @classmethod
    def advise(cls, folders: Sequence[Folder]) -> None:
        """print the command that starts a watch over the folders no watch holds, or why none can run.

        the agent starts the watch, because only a background job of its own can wake it

        # Arguments

        * `folders` - the folders, each once
        """
        watch = cls.discover()
        if watch is None:
            print(f"{TOOL}: {NO_RUNTIME}", file=sys.stderr)
        elif unwatched := [folder for folder in folders if not watch.held(folder)]:
            print(f"no watch: {cls.command(unwatched)}")

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

    def file(self, folder: Folder, suffix: str) -> Path:
        """a folder's lock or record: named by its real path, hashed.

        # Arguments

        * `folder` - the folder
        * `suffix` - LOCK or RECORD

        # Returns

        the file's path under the root
        """
        key = hashlib.sha256(str(folder.path).encode(ENCODING)).hexdigest()
        return self.root / f"{key}{suffix}"

    def held(self, folder: Folder) -> bool:
        """whether a watch holds the folder's lock.

        the probe takes a shared lock for an instant: a watch's exclusive lock
        refuses it, and another stamp's probe never does. a watch taking its
        lock in that instant finds it held, and tries again after GRACE

        # Arguments

        * `folder` - the folder

        # Returns

        True while a watch runs on it; False for a lock that cannot be opened, which no watch could have
        taken, so the watch command printed for it says why when it runs
        """
        lock = self.file(folder, LOCK)
        if not lock.is_file():
            return False
        try:
            handle = os.open(lock, os.O_RDONLY)
        except OSError:
            return False
        try:
            fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
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

        # Raises

        NoVerdict when the lock cannot be made or opened
        """
        lock = self.file(folder, LOCK)
        try:
            self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
            handle = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
        except OSError as error:
            raise NoVerdict(f"{lock} cannot be taken: {error.strerror}") from None
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
            record = json.loads(read_text(self.file(folder, RECORD)))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        if not Json.is_object(record):
            return {}
        return {name: value for name, value in record.items() if isinstance(value, str)}

    def record(self, folder: Folder, reports: dict[str, str]) -> None:
        """write a folder's reports.

        # Arguments

        * `folder` - the folder
        * `reports` - each reported item's name and fingerprint
        """
        write_text(self.file(folder, RECORD), json.dumps(reports, indent=1, sort_keys=True) + "\n")

    def look(self, folder: Folder, skipped: set[Path]) -> list[tuple[Path, ItemText]]:
        """one look at a folder: every item that wakes the watch and was not reported as it reads.

        the record forgets an item gone, unchanged or parked, so an answer of
        his after that, or an unpark bringing one back as it was, is reported
        even when it repeats one reported before. an item that does not read
        this time is kept, so it is not reported again once it reads

        # Arguments

        * `folder` - the folder
        * `skipped` - the items this watch could not read, each said once on stderr; grows here

        # Returns

        each item and its text
        """
        # --------------------------------------------------
        # every item that reads; one that does not is said once and passed by
        # --------------------------------------------------
        texts: dict[str, tuple[Path, ItemText]] = {}
        unread: set[str] = set()
        for path in folder.items():
            try:
                texts[path.name] = (path, Item(path).read())
            except NoVerdict as error:
                unread.add(path.name)
                if path not in skipped:
                    skipped.add(path)
                    print(f"{TOOL}: skipped: {error}", file=sys.stderr)
        # --------------------------------------------------
        # the record, without the items gone or settled
        # --------------------------------------------------
        reported = self.reported(folder)
        kept = {name: fingerprint for name, fingerprint in reported.items()
                if name in unread or (name in texts and texts[name][1].status.wakes)}
        if kept != reported:
            self.record(folder, kept)
        return [(path, text) for path, text in texts.values()
                if text.status.wakes and kept.get(path.name) != text.fingerprint]

    def run(self, folders: Sequence[Folder], every: float) -> Exit:
        """hold each folder's lock, then poll until an item is to report; print it, record it, and exit.

        # Arguments

        * `folders` - the folders to watch, each once
        * `every` - seconds between looks

        # Returns

        OK once something was reported, BLOCKED when another watch holds a folder

        # Raises

        NoVerdict once no watched folder exists
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
            # look until something is new, while a folder is left to look in
            # --------------------------------------------------
            skipped: set[Path] = set()
            while not (found := {folder: items for folder in folders if (items := self.look(folder, skipped))}):
                if not any(folder.path.is_dir() for folder in folders):
                    raise NoVerdict(NO_DIR.format(", ".join(str(folder.path) for folder in folders)))
                time.sleep(every)
            # --------------------------------------------------
            # each item with its note, out of the buffer, then the record, so a re-run does not repeat it
            # --------------------------------------------------
            for folder, items in found.items():
                for path, text in items:
                    print(f"{text.status} {path}")
                    for line in text.note.splitlines():
                        print(f"{NOTE_INDENT}{line}".rstrip())
                sys.stdout.flush()
                self.record(folder, self.reported(folder) | {path.name: text.fingerprint for path, text in items})
        return Exit.OK


def main(args: Args) -> Exit | None:
    """dispatch the subcommand.

    # Arguments

    * `args` - the parsed command line; the first positional is the subcommand

    # Returns

    the subcommand's verdict

    # Raises

    UsageError for an unknown subcommand, a wrong count of arguments, a flag
    another subcommand owns, a bad -e, or no text on stdin for `answer` or
    `new`; NoVerdict for an item or a folder that does not exist, or an item that cannot be read
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
            Item.stamp_all([Item.of(Path(name)) for name in rest], life)
        case Command.STATUS:
            Folder.of(Path(rest[0]) if rest else DEFAULT_DIR).status()
        case Command.QUESTION:
            print(Item.of(Path(rest[0])).read().question)
        case Command.ANSWER | Command.CLEAR:
            Item.of(Path(rest[0])).answer(args.stdin_verbatim() if command is Command.ANSWER else "")
        case Command.NEW:
            Item.of(Path(rest[0])).new(ItemText(args.stdin_verbatim()))
        case Command.RESOLVE:
            return Item.of(Path(rest[0])).resolve(life)
        case Command.PARK | Command.UNPARK:
            return Item.of(Path(rest[0])).park(life, LifeAction(command))
        case Command.WATCH:
            return Watch.start(args)
    return Exit.OK


if __name__ == "__main__":
    Tool(TOOL, __doc__, (Flag.DIR, Flag.EVERY), positionals=(1, None)).run(main)
