#!/usr/bin/env python3
"""the checks of brain-open-items, each against the script as a process, on a temp repo.

every test gets its own rig: a temp repo, its own $XDG_RUNTIME_DIR, and a PATH
holding only a stand-in `life` that logs each call, a `b-find` that runs this
checkout's brain-find.py, python and the system's bin dirs, so no test reaches
the real life, its host or the real runtime dir

    python3 agentic-files/skills/brain-open-items/test_brain_open_items.py

Author: aav
"""
# unittest's own assertions are the point of a TestCase, and the house config has no per-file-ignores
# ruff: noqa: PT009
# the brain's root is three folders up, and brainlib is in its bin/
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "bin"))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Exit, find_brain

# --------------------------------------------------
# external
# --------------------------------------------------
import fcntl
import os
import shlex
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from collections.abc import Callable, Generator, Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, replace
from functools import partial
from typing import Self

# --------------------------------------------------
# constants
# --------------------------------------------------
SCRIPT = Path(__file__).with_name("brain-open-items.py")
# the skill's own page, whose spelling of the commands a test runs
SKILL = SCRIPT.with_name("SKILL.md")
BRAIN = find_brain()
# the folder every item sits in, relative to the temp repo
FOLDER = "plans/open-items"
# seconds between a test watch's looks
EVERY = "0.05"
# the longest any one process or condition is waited for, in seconds
PATIENCE = 20.0
# how often a condition is looked at, in seconds
POLL = 0.02
# the stand-in life's status when it did what it was asked
DONE = "0"
# life's status for a refusal
REFUSED = "4"
# life's status for an item no todo backs
NO_TODO = "5"
# life's status on a machine not set up for it
NOT_SET_UP = "6"
# a footer-shaped line, as a question may quote one
QUOTED_FOOTER = "<!-- sha256: " + "a" * 64 + " -->"
# a parked section as life's projection writes it: his comment, then the parked paragraph
PARKED_WITH_COMMENT = "2026-11-03 14:02 arpad: later\n\nParked.\n"
# how often a resolve and an answer are raced
RACES = 20
# the stand-in life: one log line per call, `<args> stamped|bare` by whether the item had a footer then
LIFE = """#!/bin/sh
if grep -q '^<!-- sha256: ' "$3" 2>/dev/null; then footer=stamped; else footer=bare; fi
echo "$* $footer" >> "$FAKE_LIFE_LOG"
exit "${FAKE_LIFE_EXIT:-0}"
"""
# the stand-in b-find: this checkout's, run as module.nix's wrapper runs it
B_FIND = f"""#!/bin/sh
exec python3 -I {BRAIN / "bin" / "brain-find.py"} "$@"
"""
# a question as the agent writes it
QUESTION = "# Q02: default status\n\na todo file with no status line lands in open.\n\n## Your call\n"
# its file name
Q02 = "Q02-default-status.md"


def locks(pid: int, *, waiting: bool) -> bool:
    """whether a process holds a flock, or waits for one, by /proc/locks.

    # Arguments

    * `pid` - the process
    * `waiting` - True for a lock it waits for, False for one it holds

    # Returns

    True when /proc/locks lists such a flock
    """
    for line in Path("/proc/locks").read_text().splitlines():
        fields = line.split()
        blocked = fields[1:2] == ["->"]
        rest = fields[2:] if blocked else fields[1:]
        if blocked == waiting and rest[:1] == ["FLOCK"] and str(pid) in rest:
            return True
    return False


def until(condition: Callable[[], bool]) -> bool:
    """wait for a condition, at most PATIENCE seconds.

    # Arguments

    * `condition` - what to wait for

    # Returns

    whether it came
    """
    deadline = time.monotonic() + PATIENCE
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(POLL)
    return False


@dataclass(frozen=True)
class Rig:
    """one test's temp repo, runtime dir and PATH, and the script run against them."""

    # the temp repo, cwd of every run
    repo: Path
    # the stand-in life's log
    log: Path
    # the environment every run gets
    env: Mapping[str, str]
    # closes every file and reaps every process the test started
    stack: ExitStack

    @classmethod
    def of(cls, case: unittest.TestCase) -> Self:
        """make a rig that lives as long as the test.

        # Arguments

        * `case` - the test

        # Returns

        the rig
        """
        scratch = Path(case.enterContext(tempfile.TemporaryDirectory()))
        (scratch / "repo" / FOLDER).mkdir(parents=True)
        (scratch / "bin").mkdir()
        for name, text in (("life", LIFE), ("b-find", B_FIND)):
            (scratch / "bin" / name).write_text(text)
            (scratch / "bin" / name).chmod(0o755)
        (scratch / "run").mkdir(mode=0o700)
        path = os.pathsep.join((str(scratch / "bin"), str(Path(sys.executable).parent), "/usr/bin", "/bin"))
        case.assertEqual(shutil.which("life", path=path), str(scratch / "bin" / "life"))
        env = {"PATH": path, "HOME": str(scratch), "XDG_RUNTIME_DIR": str(scratch / "run"),
               "FAKE_LIFE_LOG": str(scratch / "life.log")}
        return cls(scratch / "repo", scratch / "life.log", env, case.enterContext(ExitStack()))

    @property
    def folder(self) -> Path:
        """the repo's open-items folder.

        # Returns

        its path
        """
        return self.repo / FOLDER

    @property
    def bin(self) -> Path:
        """the folder of the stand-in life, first on PATH.

        # Returns

        its path
        """
        return self.repo.parent / "bin"

    def shown(self, name: str = Q02) -> Path:
        """an item's path as watch prints it: under the folder's real path.

        # Arguments

        * `name` - the item's file name

        # Returns

        the path
        """
        return self.folder.resolve() / name

    def without(self, name: str) -> Self:
        """the same rig, its runs never given one environment variable.

        # Arguments

        * `name` - the variable

        # Returns

        the rig
        """
        return replace(self, env={key: value for key, value in self.env.items() if key != name})

    def run(self, *args: str, stdin: str = "", life: str = DONE) -> subprocess.CompletedProcess[str]:
        """run the script to its end, in the repo.

        # Arguments

        * `args` - its arguments
        * `stdin` - its stdin
        * `life` - the status the stand-in life exits with

        # Returns

        the finished process
        """
        # the script under test, its arguments the test's own; no shell (S603)
        return subprocess.run([sys.executable, str(SCRIPT), *args],  # noqa: S603
                              cwd=self.repo, input=stdin, text=True, capture_output=True,
                              env={**self.env, "FAKE_LIFE_EXIT": life}, timeout=PATIENCE, check=False)

    def start(self, *args: str, stdin: str = "", life: str = DONE) -> subprocess.Popen[str]:
        """start the script in the background, in the repo.

        # Arguments

        * `args` - its arguments
        * `stdin` - its stdin
        * `life` - the status the stand-in life exits with

        # Returns

        the running process, its stdin already written and closed, so it never waits on the test for it
        """
        # --------------------------------------------------
        # stdin through a pipe filled and closed up front; a test's stdin fits the pipe's buffer
        # --------------------------------------------------
        reader, writer = os.pipe()
        os.write(writer, stdin.encode())
        os.close(writer)
        # the script under test, its arguments the test's own; no shell (S603)
        process = subprocess.Popen([sys.executable, str(SCRIPT), *args],  # noqa: S603
                                   cwd=self.repo, stdin=reader, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env={**self.env, "FAKE_LIFE_EXIT": life})
        os.close(reader)
        self.stack.callback(self.reap, process)
        return process

    @staticmethod
    def reap(process: subprocess.Popen[str]) -> None:
        """kill a process the test left running, and wait for it.

        # Arguments

        * `process` - the process
        """
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=PATIENCE)

    def watch(self) -> subprocess.CompletedProcess[str]:
        """run a watch over the folder until it reports.

        # Returns

        the finished watch
        """
        return self.run("watch", "--dir", FOLDER, "--every", EVERY)

    def watching(self) -> subprocess.Popen[str]:
        """start a watch over the folder, and wait until it holds the folder's lock.

        # Returns

        the running watch

        # Raises

        AssertionError when it never takes the lock
        """
        process = self.start("watch", "--dir", FOLDER, "--every", EVERY)
        if not until(partial(locks, process.pid, waiting=False)):
            raise AssertionError("the watch never took its lock")
        return process

    def item(self, name: str = Q02, text: str = QUESTION) -> Path:
        """write an item, unstamped.

        # Arguments

        * `name` - its file name
        * `text` - its text

        # Returns

        its path
        """
        path = self.folder / name
        path.write_text(text)
        return path

    @contextmanager
    def locked(self) -> Generator[None]:
        """hold the folder's write lock, as life's ask or another write would."""
        handle = os.open(self.folder, os.O_RDONLY | os.O_DIRECTORY)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield
        finally:
            os.close(handle)

    def life_calls(self) -> list[str]:
        """every call the stand-in life logged.

        # Returns

        one line per call
        """
        return self.log.read_text().splitlines() if self.log.exists() else []


class Watching(unittest.TestCase):
    """the watch: what it reports, once, and the locks that keep one watch per folder."""

    def test_watch_prints_new_then_edited_with_the_note(self) -> None:
        """`watch` prints `new`, then `edited` with the note."""
        rig = Rig.of(self)
        path = rig.item()
        first = rig.watch()
        self.assertEqual((first.returncode, first.stdout), (Exit.OK, f"new {rig.shown()}\n"))
        self.assertEqual(rig.run("stamp", str(path), life=NO_TODO).returncode, Exit.OK)
        path.write_text(path.read_text().replace("## Your call\n", "## Your call\n\nbacklog, and\nsay why\n"))
        second = rig.watch()
        self.assertEqual((second.returncode, second.stdout),
                         (Exit.OK, f"edited {rig.shown()}\n  backlog, and\n  say why\n"))

    def test_watch_skips_a_parked_item_with_comments_above_parked(self) -> None:
        """it skips an item whose section ends with a `Parked.` paragraph, his comments above it."""
        rig = Rig.of(self)
        rig.item("Q01-parked.md", QUESTION + "\n" + PARKED_WITH_COMMENT)
        rig.item()
        self.assertEqual(rig.watch().stdout, f"new {rig.shown()}\n")

    def test_a_second_watch_says_already_watching(self) -> None:
        """a second `watch` says "already watching"."""
        rig = Rig.of(self)
        first = rig.watching()
        second = rig.watch()
        self.assertEqual(second.returncode, Exit.BLOCKED)
        self.assertIn(f"already watching {rig.folder.resolve()}", second.stderr)
        self.assertIsNone(first.poll())

    def test_one_folder_named_twice_is_watched_once(self) -> None:
        """a folder named relative and absolute is one folder: the watch does not block itself."""
        rig = Rig.of(self)
        rig.item()
        done = rig.run("watch", "--dir", FOLDER, "--dir", str(rig.folder), "--every", EVERY)
        self.assertEqual((done.returncode, done.stdout), (Exit.OK, f"new {rig.shown()}\n"))

    def test_a_killed_watch_does_not_block_the_next(self) -> None:
        """a killed watch does not block the next one."""
        rig = Rig.of(self)
        first = rig.watching()
        first.send_signal(signal.SIGKILL)
        first.communicate(timeout=PATIENCE)
        rig.item()
        second = rig.watch()
        self.assertEqual((second.returncode, second.stdout), (Exit.OK, f"new {rig.shown()}\n"))

    def test_a_rerun_does_not_repeat_an_item(self) -> None:
        """a re-run does not repeat an item."""
        rig = Rig.of(self)
        rig.item("Q01-first.md")
        self.assertEqual(rig.watch().stdout, f"new {rig.shown('Q01-first.md')}\n")
        rig.item()
        self.assertEqual(rig.watch().stdout, f"new {rig.shown()}\n")

    def test_an_answer_repeated_after_a_stamp_is_reported_again(self) -> None:
        """an answer reported, then settled by a stamp, is reported again when it comes back as it was."""
        rig = Rig.of(self)
        path = rig.item()
        rig.run("stamp", str(path), life=NO_TODO)
        stamped = path.read_text()
        answered = stamped.replace("## Your call\n", "## Your call\n\nyes\n")
        reported = f"edited {rig.shown()}\n  yes\n"
        # --------------------------------------------------
        # his answer, reported
        # --------------------------------------------------
        path.write_text(answered)
        self.assertEqual(rig.watch().stdout, reported)
        # --------------------------------------------------
        # the item back as stamped, seen by a watch that reports another item
        # --------------------------------------------------
        path.write_text(stamped)
        rig.item("Q03-other.md")
        self.assertEqual(rig.watch().stdout, f"new {rig.shown('Q03-other.md')}\n")
        # --------------------------------------------------
        # the same answer again
        # --------------------------------------------------
        path.write_text(answered)
        self.assertEqual(rig.watch().stdout, reported)

    def test_an_unreadable_item_is_skipped_with_one_line(self) -> None:
        """watch skips an item that does not decode, says so on one stderr line, and reports the rest."""
        rig = Rig.of(self)
        (rig.folder / "Q01-binary.md").write_bytes(b"\xff\xfe")
        rig.item()
        done = rig.watch()
        self.assertEqual((done.returncode, done.stdout), (Exit.OK, f"new {rig.shown()}\n"))
        self.assertEqual(len(done.stderr.splitlines()), 1, done.stderr)
        self.assertIn(f"skipped: {rig.shown('Q01-binary.md')} cannot be read", done.stderr)

    def test_a_watch_whose_folder_is_gone_exits(self) -> None:
        """a watch exits FAILED once its folder is gone."""
        rig = Rig.of(self)
        watch = rig.watching()
        shutil.rmtree(rig.folder)
        _, stderr = watch.communicate(timeout=PATIENCE)
        self.assertEqual(watch.returncode, Exit.FAILED)
        self.assertIn("no open-items dir at", stderr)

    def test_an_answer_racing_a_resolve_never_brings_the_file_back(self) -> None:
        """an `answer` racing a `resolve` never brings the file back."""
        rig = Rig.of(self)
        # --------------------------------------------------
        # the answer reaches the lock, the resolve's delete lands first: the answer finds no item
        # --------------------------------------------------
        path = rig.item()
        with rig.locked():
            answer = rig.start("answer", str(path), stdin="yes\n")
            self.assertTrue(until(partial(locks, answer.pid, waiting=True)), "the answer never waited")
            path.unlink()
        _, stderr = answer.communicate(timeout=PATIENCE)
        self.assertEqual(answer.returncode, Exit.FAILED)
        self.assertIn("no item at", stderr)
        self.assertFalse(path.exists())
        # --------------------------------------------------
        # the two as processes, started together, many times
        # --------------------------------------------------
        for _ in range(RACES):
            rig.item()
            resolve = rig.start("resolve", str(path))
            answer = rig.start("answer", str(path), stdin="yes\n")
            for process in (resolve, answer):
                process.communicate(timeout=PATIENCE)
            self.assertEqual(resolve.returncode, Exit.OK)
            self.assertFalse(path.exists())

    def test_every_write_waits_for_the_folder_lock_and_none_for_the_watch_lock(self) -> None:
        """every write takes the folder's write lock, which is separate from watch's lock."""
        rig = Rig.of(self)
        path = rig.folder / Q02
        writes = (("stamp", str(path)), ("answer", str(path)), ("park", str(path)),
                  ("new", str(rig.folder / "U-x.md")), ("resolve", str(path)))
        for args in writes:
            with self.subTest(command=args[0]):
                rig.item()
                with rig.locked():
                    write = rig.start(*args, stdin="x\n", life=NO_TODO)
                    self.assertTrue(until(partial(locks, write.pid, waiting=True)), "the write never waited")
                write.communicate(timeout=PATIENCE)
                self.assertEqual(write.returncode, Exit.OK)
        for left in rig.folder.iterdir():
            left.unlink()
        rig.watching()
        rig.item()
        self.assertEqual(rig.run("answer", str(path), stdin="x\n").returncode, Exit.OK)


class Stamping(unittest.TestCase):
    """`stamp`: life asked first, the footer, and the watch command it prints."""

    def test_stamp_asks_life_first_and_stamps_whatever_it_replied(self) -> None:
        """`stamp` asks life before the footer is written, and stamps when life refuses."""
        rig = Rig.of(self)
        path = rig.item()
        self.assertEqual(rig.run("stamp", str(path), life=REFUSED).returncode, Exit.OK)
        self.assertEqual(rig.life_calls(), [f"open-item ask {path} bare"])
        self.assertEqual(rig.run("status").stdout, f"unchanged {Q02}\n")

    def test_stamp_prints_the_watch_command_only_when_no_watch_runs(self) -> None:
        """`stamp` prints the watch command only when no watch runs, and the command it prints runs."""
        rig = Rig.of(self)
        path = rig.item()
        alone = rig.run("stamp", str(path)).stdout.splitlines()
        self.assertEqual(alone[0], f"stamped {path}")
        command = alone[1].removeprefix("no watch: ")
        self.assertEqual(shlex.split(command), ["python3", str(SCRIPT), "watch", "--dir", str(rig.folder.resolve())])
        watch = rig.start(*shlex.split(command)[2:])
        self.assertTrue(until(partial(locks, watch.pid, waiting=False)), "the printed watch never took its lock")
        self.assertEqual(rig.run("stamp", str(path)).stdout, f"stamped {path}\n")

    def test_stamp_names_a_folder_named_twice_once(self) -> None:
        """two items in one folder, named relative and absolute, print one `--dir`, the folder's real path."""
        rig = Rig.of(self)
        rig.item()
        rig.item("Q03-other.md")
        done = rig.run("stamp", f"{FOLDER}/{Q02}", str(rig.folder / "Q03-other.md"))
        command = done.stdout.splitlines()[-1].removeprefix("no watch: ")
        self.assertEqual(shlex.split(command)[3:], ["--dir", str(rig.folder.resolve())])

    def test_stamp_without_a_runtime_dir_says_why_no_watch_can_run(self) -> None:
        """with $XDG_RUNTIME_DIR unset, `stamp` prints the reason, never a watch command that would fail."""
        rig = Rig.of(self)
        path = rig.item()
        done = rig.without("XDG_RUNTIME_DIR").run("stamp", str(path))
        self.assertEqual((done.returncode, done.stdout), (Exit.OK, f"stamped {path}\n"))
        self.assertIn("$XDG_RUNTIME_DIR is no absolute path", done.stderr)

    def test_stamp_touches_nothing_when_an_item_is_missing(self) -> None:
        """`stamp a b` with `b` missing asks life nothing and leaves `a` unstamped."""
        rig = Rig.of(self)
        path = rig.item()
        done = rig.run("stamp", str(path), str(rig.folder / "Q09-none.md"))
        self.assertEqual(done.returncode, Exit.FAILED)
        self.assertEqual((rig.life_calls(), path.read_text()), ([], QUESTION))

    def test_stamp_reads_unchanged_for_an_item_opening_with_a_blank_line(self) -> None:
        """an item that opens with a blank line reads `unchanged` right after its stamp."""
        rig = Rig.of(self)
        path = rig.item(text="\n" + QUESTION)
        rig.run("stamp", str(path))
        self.assertEqual(rig.run("status").stdout, f"unchanged {Q02}\n")

    def test_stamp_keeps_a_footer_quoted_in_the_question_and_writes_nothing_twice(self) -> None:
        """a footer-shaped line above the heading is the question's; a second stamp writes nothing."""
        rig = Rig.of(self)
        path = rig.item(text=f"# Q02: the footer\n\nit reads\n\n{QUOTED_FOOTER}\n\n## Your call\n")
        rig.run("stamp", str(path))
        self.assertIn(f"\n{QUOTED_FOOTER}\n\n## Your call\n", path.read_text())
        self.assertEqual(rig.run("status").stdout, f"unchanged {Q02}\n")
        inode = path.stat().st_ino
        rig.run("stamp", str(path))
        self.assertEqual(path.stat().st_ino, inode)


class Commands(unittest.TestCase):
    """the commands that write an item but `stamp`, `status`, and the skill's own spelling of them."""

    def test_every_command_in_the_skill_runs_as_written(self) -> None:
        """every command runs as SKILL.md spells it, its `B=` line first."""
        rig = Rig.of(self)
        rig.item()
        (rig.repo / "section.md").write_text("backlog\n")
        (rig.repo / "body.md").write_text("# U: the visuals are bad\n\nthe board scrolls sideways.\n")
        setup = next((line for line in SKILL.read_text().splitlines() if line.startswith("B=")), None)
        self.assertIsNotNone(setup, f"{SKILL} sets no B")
        lines = f"""set -e
eval "$(b-find -e)"
{setup}
test "$B" -ef {shlex.quote(str(SCRIPT))}
python3 "$B" stamp plans/open-items/Q02-default-status.md
python3 "$B" answer plans/open-items/Q02-default-status.md < section.md
python3 "$B" park plans/open-items/Q02-default-status.md
python3 "$B" unpark plans/open-items/Q02-default-status.md
python3 "$B" new plans/open-items/U-the-visuals-are-bad.md < body.md
python3 "$B" status
python3 "$B" watch --dir plans/open-items --every 30
python3 "$B" resolve plans/open-items/Q02-default-status.md
"""
        # the commands as the skill spells them, which take a shell to run as written (S603)
        done = subprocess.run([shutil.which("bash") or "bash", "-c", lines],  # noqa: S603
                              cwd=rig.repo, text=True, capture_output=True, env=dict(rig.env),
                              timeout=PATIENCE, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(f"new {FOLDER}/U-the-visuals-are-bad.md\n", done.stdout)
        item = rig.folder / Q02
        self.assertEqual([call.split()[:3] for call in rig.life_calls()],
                         [["open-item", action, str(item)] for action in ("ask", "park", "unpark", "resolve")])
        self.assertFalse(item.exists())

    def test_brain_lint_passes(self) -> None:
        """`brain-lint.py` passes on the skill's python."""
        # the brain's own linter on the skill's own folder; no shell (S603)
        done = subprocess.run([sys.executable, str(BRAIN / "bin" / "check" / "brain-lint.py"),  # noqa: S603
                               str(SCRIPT.parent.relative_to(BRAIN))], cwd=BRAIN, text=True,
                              capture_output=True, timeout=10 * PATIENCE, check=False)
        self.assertEqual(done.returncode, Exit.OK, done.stdout + done.stderr)

    def test_status_lists_the_items_carrying_his_input_first(self) -> None:
        """`status` lists edited, new, parked, then unchanged; a parked item reads `parked`."""
        rig = Rig.of(self)
        for name in ("A-edited.md", "B-unchanged.md"):
            rig.run("stamp", str(rig.item(name)), life=NO_TODO)
        edited = rig.folder / "A-edited.md"
        edited.write_text(edited.read_text().replace("## Your call\n", "## Your call\n\nyes\n"))
        rig.item("C-parked.md", QUESTION + "\n" + PARKED_WITH_COMMENT)
        rig.item("D-new.md")
        self.assertEqual(rig.run("status").stdout,
                         "edited    A-edited.md\nnew       D-new.md\nparked    C-parked.md\nunchanged B-unchanged.md\n")

    def test_an_unreadable_item_fails_status_and_answer_on_one_line(self) -> None:
        """an item that does not decode fails `status`, a folder named as an item fails `answer`, each in one line."""
        rig = Rig.of(self)
        (rig.folder / "Q01-binary.md").write_bytes(b"\xff\xfe")
        status = rig.run("status")
        answer = rig.run("answer", str(rig.folder), stdin="x\n")
        for done in (status, answer):
            self.assertEqual((done.returncode, len(done.stderr.splitlines())), (Exit.FAILED, 1), done.stderr)
        self.assertIn("cannot be read", status.stderr)
        self.assertIn("no item at", answer.stderr)

    def test_answer_replaces_the_section_and_refuses_a_missing_item(self) -> None:
        """`answer` replaces `## Your call` whole and keeps the footer; it refuses an item that does not exist."""
        rig = Rig.of(self)
        path = rig.item(text=QUESTION + "\nold\n")
        rig.run("stamp", str(path))
        footer = path.read_text().splitlines()[-1]
        self.assertEqual(rig.run("answer", str(path), stdin="\n  - new\n").returncode, Exit.OK)
        self.assertEqual(path.read_text(), QUESTION + "\n  - new\n\n" + footer + "\n")
        missing = rig.folder / "Q09-none.md"
        self.assertEqual(rig.run("answer", str(missing), stdin="x\n").returncode, Exit.FAILED)
        self.assertFalse(missing.exists())

    def test_answer_and_new_refuse_empty_stdin(self) -> None:
        """`answer` and `new` with nothing on stdin, as an agent's forgotten redirect gives them, write nothing."""
        rig = Rig.of(self)
        path = rig.item(text=QUESTION + "\nhis answer\n")
        for stdin in ("", " \n\n"):
            with self.subTest(stdin=stdin):
                self.assertEqual(rig.run("answer", str(path), stdin=stdin).returncode, Exit.USAGE)
                self.assertEqual(path.read_text(), QUESTION + "\nhis answer\n")
                self.assertEqual(rig.run("new", str(rig.folder / "U-x.md"), stdin=stdin).returncode, Exit.USAGE)
                self.assertFalse((rig.folder / "U-x.md").exists())

    def test_new_makes_an_unstamped_item_and_refuses_a_taken_path(self) -> None:
        """`new` makes an unstamped item, its folder too, and never writes over one."""
        rig = Rig.of(self)
        path = rig.repo / "other" / FOLDER / "U-x.md"
        self.assertEqual(rig.run("new", str(path), stdin="# U: x\n").returncode, Exit.OK)
        self.assertEqual(path.read_text(), "# U: x\n\n## Your call\n")
        self.assertEqual(rig.run("new", str(path), stdin="# U: y\n").returncode, Exit.FAILED)
        self.assertEqual(path.read_text(), "# U: x\n\n## Your call\n")

    def test_resolve_deletes_only_when_life_succeeded(self) -> None:
        """`resolve` keeps the item when life refuses, and deletes it when life resolved it or no todo backs it."""
        rig = Rig.of(self)
        for no_todo in (NO_TODO, NOT_SET_UP):
            with self.subTest(life=no_todo):
                path = rig.item()
                self.assertEqual(rig.run("resolve", str(path), life=REFUSED).returncode, Exit.FAILED)
                self.assertTrue(path.exists())
                self.assertEqual(rig.run("resolve", str(path), life=no_todo).returncode, Exit.OK)
                self.assertFalse(path.exists())

    def test_a_life_that_cannot_run_is_a_refusal_in_one_line(self) -> None:
        """a `life` on PATH that cannot run refuses `resolve` in one stderr line, and the item stays."""
        rig = Rig.of(self)
        (rig.bin / "life").write_text("#!/nonexistent/interpreter\n")
        path = rig.item()
        done = rig.run("resolve", str(path))
        self.assertEqual((done.returncode, len(done.stderr.splitlines())), (Exit.FAILED, 1), done.stderr)
        self.assertIn("cannot run", done.stderr)
        self.assertTrue(path.exists())

    def test_park_keeps_his_answer_and_unpark_drops_only_parked(self) -> None:
        """`park` keeps his answer above a `Parked.` paragraph, and `unpark` drops only that paragraph.

        with a todo, both leave the item to life
        """
        rig = Rig.of(self)
        answered = QUESTION + "\nhis answer\n"
        path = rig.item(text=answered)
        self.assertEqual(rig.run("park", str(path)).returncode, Exit.OK)
        self.assertEqual(path.read_text(), answered)
        self.assertEqual(rig.run("unpark", str(path), life=NO_TODO).returncode, Exit.OK)
        self.assertEqual(path.read_text(), answered)
        self.assertEqual(rig.run("park", str(path), life=NOT_SET_UP).returncode, Exit.OK)
        self.assertEqual(path.read_text(), QUESTION + "\nhis answer\n\nParked.\n")
        self.assertEqual(rig.run("status").stdout, f"parked    {Q02}\n")
        self.assertEqual(rig.run("unpark", str(path), life=NO_TODO).returncode, Exit.OK)
        self.assertEqual(path.read_text(), answered)

    def test_park_folds_text_typed_below_the_footer_into_the_section(self) -> None:
        """an answer typed below the footer moves above it when the item is parked, and the item reads parked."""
        rig = Rig.of(self)
        path = rig.item()
        rig.run("stamp", str(path))
        footer = path.read_text().splitlines()[-1]
        path.write_text(path.read_text() + "yes\n")
        self.assertEqual(rig.run("park", str(path), life=NO_TODO).returncode, Exit.OK)
        self.assertEqual(path.read_text(), QUESTION + "\nyes\n\nParked.\n\n" + footer + "\n")
        self.assertEqual(rig.run("status").stdout, f"parked    {Q02}\n")


if __name__ == "__main__":
    unittest.main()
