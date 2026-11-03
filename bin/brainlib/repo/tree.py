"""brainlib.repo.tree: what a git tree is - its repos, and the files each one lists.

a tree is the outermost repo around a directory and every submodule under it.
every listing asks git for nul-separated names, so a path holding a space, a
newline or a non-ascii character comes back as written, and a git that cannot
answer raises RepoError rather than reading as an empty repo. every git
command the brain runs is one GitRun, which says how it ended

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.text import read_text
from brainlib.vocab import GIT_TIMEOUT, NoVerdict

# --------------------------------------------------
# external
# --------------------------------------------------
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import ClassVar

# --------------------------------------------------
# constants
# --------------------------------------------------
# the mode git gives a submodule's entry in its parent's index
GITLINK_MODE = "160000"
# the status `RepoTree.since` gives a file git does not track
UNTRACKED = "?"
# the top-level directory of a repo that holds his scratch and open items
PLANS = "plans"
# the most lines `GitRun.detail` gives: what a hook said, then git's own word
DETAIL_LINES = 5
# how each stderr line git writes itself opens; what a hook printed comes before the first
GIT_SAYS = ("error:", "fatal:", "warning:", "hint:")
# how git's own word on a failure opens
GIT_FAILS = ("error:", "fatal:")
# what git puts before each line it relays from the remote, a pre-receive hook's output among them
RELAYED = "remote:"
# the global options git reads the next argument as the value of
VALUED_OPTIONS = frozenset({"-c", "-C", "--git-dir", "--work-tree", "--namespace"})
# the flag opening each ref row of a `--porcelain` push: up to date, forced, deleted, new, done, refused
PORCELAIN_FLAGS = frozenset(" +-*=!")


class Ending(StrEnum):
    """how one git command ended."""

    # exited 0
    OK = "ok"
    # a ref update git refused as not a fast-forward of the other side's tip: every `!` row of
    # `--porcelain` output reads `[rejected] (non-fast-forward)` or `[rejected] (fetch first)`
    REJECTED = "rejected"
    # exited non-zero for any other reason, or could not start
    FAILED = "failed"
    # ran past its timeout and was killed
    TIMED_OUT = "timed out"


@dataclass(frozen=True)
class GitRun:
    """one git command run in a repo, and how it ended."""

    repo: Path
    argv: tuple[str, ...]
    ending: Ending
    # decoded as the filesystem decodes a name (os.fsdecode)
    stdout: str
    # git's stderr; for a run that never exited, why
    stderr: str
    # None when git did not exit: missing, unstartable, timed out
    code: int | None
    # the porcelain summaries of a refused non-fast-forward update
    NOT_FAST_FORWARD: ClassVar[frozenset[str]] = frozenset({"[rejected] (non-fast-forward)",
                                                           "[rejected] (fetch first)"})

    @classmethod
    def of(cls, repo: Path, *argv: str, timeout: float = GIT_TIMEOUT) -> "GitRun":
        r"""run a git command in a repo and say how it ended; this never raises.

        the inherited `GIT_*` environment is dropped, since GIT_DIR and
        GIT_WORK_TREE outrank `-C` and would silently answer about a DIFFERENT
        repo. output is decoded the way the filesystem decodes a name
        (`os.fsdecode`), so a name that is not utf-8 maps back to the same path
        and a `\r` inside a name is not rewritten as a newline

        # Arguments

        * `repo` - the repository to run in
        * `argv` - git's global options, then the subcommand and its arguments
        * `timeout` - seconds before the command is killed

        # Returns

        the run: OK, REJECTED or FAILED with git's exit code, or FAILED or
        TIMED_OUT with no code and the reason in `stderr`

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     run = GitRun.of(Path(tmp), "rev-parse", "HEAD")
            ...     run.ending, run.code, str(run).replace(tmp, "TMP")
            (<Ending.FAILED: 'failed'>, 128, '`git rev-parse HEAD` in TMP exited 128')
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     run = GitRun.of(Path(tmp), "-c", "alias.nap=!sleep 2", "nap", timeout=0.1)
            ...     run.ending, run.code, run.stderr
            (<Ending.TIMED_OUT: 'timed out'>, None, 'ran past its 0.1s timeout')
        """
        # --------------------------------------------------
        # no git on the path means no run
        # --------------------------------------------------
        found = shutil.which("git")
        if found is None:
            return cls(repo, argv, Ending.FAILED, "", "could not run: git is not on PATH", None)
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        # --------------------------------------------------
        # run git in the repo; each way it can fail is an ending
        # --------------------------------------------------
        # argv is the caller's own literals plus a discovered repo path; nothing here
        # is remote input, and shell=False keeps it an exec not a shell (S603)
        try:
            done = subprocess.run([found, "-C", str(repo), *argv], capture_output=True,  # noqa: S603
                                  check=False, env=env, timeout=timeout)
        except subprocess.TimeoutExpired:
            return cls(repo, argv, Ending.TIMED_OUT, "", f"ran past its {timeout}s timeout", None)
        except (OSError, subprocess.SubprocessError) as broken:
            return cls(repo, argv, Ending.FAILED, "", f"could not run: {broken}", None)
        stdout = os.fsdecode(done.stdout)
        return cls(repo, argv, cls._ending(done.returncode, stdout), stdout, os.fsdecode(done.stderr), done.returncode)

    @classmethod
    def _ending(cls, code: int, stdout: str) -> Ending:
        r"""the ending of a git that exited, read off the `!\t` rows a `--porcelain` push or fetch prints.

        # Arguments

        * `code` - git's exit code
        * `stdout` - git's stdout

        # Returns

        OK on 0; REJECTED when there is a `!` row and every one is a refused
        non-fast-forward; FAILED otherwise

        # Example

            >>> rows = ("!\tHEAD:refs/heads/main\t[rejected] (fetch first)",
            ...         "!\tHEAD:refs/heads/main\t[rejected] (non-fast-forward)",
            ...         "!\tHEAD:refs/heads/main\t[remote rejected] (pre-receive hook declined)")
            >>> [GitRun._ending(1, f"To /srv/origin.git\n{row}\nDone\n").value for row in rows]
            ['rejected', 'rejected', 'failed']
            >>> GitRun._ending(0, ""), GitRun._ending(128, "")
            (<Ending.OK: 'ok'>, <Ending.FAILED: 'failed'>)
        """
        if code == 0:
            return Ending.OK
        refused = cls._refused(stdout)
        return Ending.REJECTED if refused and set(refused) <= cls.NOT_FAST_FORWARD else Ending.FAILED

    @staticmethod
    def _refused(stdout: str) -> list[str]:
        r"""the summary of each ref update a `--porcelain` push or fetch refused.

        # Arguments

        * `stdout` - git's stdout

        # Returns

        each `!` row's summary, in git's order; empty for any other output
        """
        # each refused row is `!<TAB>from:to<TAB>summary`
        return [row.rsplit("\t", 1)[-1] for row in stdout.splitlines() if row.startswith("!\t")]

    @property
    def ok(self) -> bool:
        """whether git exited 0.

        # Returns

        True for an OK ending
        """
        return self.ending is Ending.OK

    @property
    def subcommand(self) -> str:
        """the git subcommand this run ran, past git's global options.

        # Returns

        the first argument that is neither a global option nor such an option's
        value; "" when there is none

        # Example

            >>> GitRun(Path("/r"), ("-c", "user.name=push", "-C", "/x", "--no-replace-objects", "push", "origin"),
            ...        Ending.OK, "", "", 0).subcommand
            'push'
        """
        args = iter(self.argv)
        for arg in args:
            if arg in VALUED_OPTIONS:
                next(args, None)
            elif not arg.startswith("-"):
                return arg
        return ""

    @property
    def detail(self) -> str:
        r"""git's reason, at most DETAIL_LINES lines: what a hook said, then git's own word.

        a hook's text reaches git's output three ways: a pre-receive hook's as
        `remote:` lines on stderr, a pre-push hook's stderr as plain lines ahead
        of git's own `error:`, and a pre-push hook's stdout on a push's stdout,
        outside the porcelain rows. git's own word is the first `!` row's summary
        when the push printed one, else the first `error:`/`fatal:` line after
        the hook's text, else the first line git wrote itself

        # Returns

        one line per thing said, the hook's first lines kept when it said more
        than fits; "" when git said nothing

        # Example

            >>> receive = GitRun(Path("/r"), ("push", "--porcelain"), Ending.FAILED,
            ...     "To /srv/o.git\n!\tHEAD:refs/heads/main\t[remote rejected] (pre-receive hook declined)\nDone\n",
            ...     "remote: refused by policy        \nremote:        \n"
            ...     "error: failed to push some refs to '/srv/o.git'\n", 1)
            >>> print(receive.detail)
            refused by policy
            [remote rejected] (pre-receive hook declined)
            >>> pre_push = GitRun(Path("/r"), ("push", "--porcelain"), Ending.FAILED, "To deploy, tag first\n",
            ...     "To push here, sign the commit\nerror: failed to push some refs to '/srv/o.git'\n", 1)
            >>> print(pre_push.detail)
            To deploy, tag first
            To push here, sign the commit
            error: failed to push some refs to '/srv/o.git'
            >>> fetch = GitRun(Path("/r"), ("fetch", "nowhere"), Ending.FAILED, "",
            ...     "fatal: 'nowhere' does not appear to be a git repository\n"
            ...     "fatal: Could not read from remote repository.\n\nand the repository exists.\n", 128)
            >>> print(fetch.detail)
            fatal: 'nowhere' does not appear to be a git repository
            >>> chatty = GitRun(Path("/r"), ("push",), Ending.FAILED, "",
            ...     "".join(f"remote: rule {n}\n" for n in range(9)) + "error: failed to push some refs\n", 1)
            >>> chatty.detail.splitlines()
            ['rule 0', 'rule 1', 'rule 2', 'rule 3', 'error: failed to push some refs']
        """
        # --------------------------------------------------
        # stderr up to git's first own line is the hook's; a push's stdout outside its rows is too
        # --------------------------------------------------
        lines = [line.strip() for line in self.stderr.splitlines()]
        first = next((at for at, line in enumerate(lines) if line.startswith(GIT_SAYS)), len(lines))
        pushed = self.subcommand == "push"
        echoed = self._hook_stdout(self.stdout) if pushed else []
        hook = [said for line in (*echoed, *lines[:first]) if (said := line.removeprefix(RELAYED).strip())]
        # --------------------------------------------------
        # git's own word: the refused row, else its first failure line, else its first line
        # --------------------------------------------------
        own = [line for line in lines[first:] if line]
        word = self._refused(self.stdout)[:1] or [line for line in own if line.startswith(GIT_FAILS)][:1] or own[:1]
        return "\n".join([*hook[:DETAIL_LINES - len(word)], *word])

    @staticmethod
    def _hook_stdout(stdout: str) -> list[str]:
        r"""the lines of a push's stdout that are not git's own `--porcelain` output: a pre-push hook's.

        git's lines are each `<flag>\t...` ref row, `Done`, and the `To <url>`
        line that heads the rows; a hook's own line opening `To ` is kept

        # Arguments

        * `stdout` - the push's stdout

        # Returns

        the hook's lines, in order

        # Example

            >>> GitRun._hook_stdout("To deploy, tag first\nTo /srv/o.git\n \tHEAD:refs/heads/main\t[up to date]\n"
            ...                     "Done\n")
            ['To deploy, tag first']
        """
        lines = stdout.splitlines()
        rows = [line[1:2] == "\t" and line[:1] in PORCELAIN_FLAGS for line in lines]
        return [line for at, line in enumerate(lines)
                if not (rows[at] or line == "Done" or (line.startswith("To ") and rows[at + 1:at + 2] == [True]))]

    def __str__(self) -> str:
        """the command, where it ran, and its exit code - or, when it never exited, why.

        # Returns

        "`git <argv>` in <repo> exited <code>", the command quoted as a shell would
        re-run it, or the same with the reason in place of the code

        # Example

            >>> print(GitRun(Path("/r"), ("commit", "-m", "two words"), Ending.FAILED, "", "", 1))
            `git commit -m 'two words'` in /r exited 1
        """
        where = f"`{shlex.join(('git', *self.argv))}` in {self.repo}"
        return f"{where} {self.stderr}" if self.code is None else f"{where} exited {self.code}"


class RepoError(NoVerdict):
    """git could not answer about a repo; a caller never reads this as an empty answer."""

    def __init__(self, run: GitRun) -> None:
        """the run that gave no answer.

        # Arguments

        * `run` - the git command, where it ran, and how it ended
        """
        super().__init__(str(run))


def git(repo: Path, *argv: str, timeout: float = GIT_TIMEOUT) -> str | None:
    """run a git command in a repo and return its stdout, or None when it gave no answer.

    None and "" are different answers and the distinction is load-bearing: a
    caller that cannot tell "git said nothing" from "git could not run" reports
    a clean scan of a repo it never opened. a caller that must say WHY git gave
    no answer calls `RepoTree.ask`, which this wraps

    # Arguments

    * `repo` - the repository to run in
    * `argv` - the git subcommand and its arguments
    * `timeout` - seconds before the command counts as failed

    # Returns

    stdout on success; None when git is missing, the path is not a repo, or the
    command failed or timed out
    """
    try:
        return RepoTree.ask(repo, *argv, timeout=timeout)
    except RepoError:
        return None


@dataclass(frozen=True)
class Change:
    """one file changed since a ref, as `RepoTree.since` lists it."""

    # absolute; for a rename, the file's new name
    path: Path
    # git's one-letter status, as `--name-status` prints it, or UNTRACKED
    status: str
    # (added, removed) lines as git counts them; None for a binary file, and for an untracked one git never counts
    counts: tuple[int, int] | None

    def lines(self) -> int | None:
        """the changed lines: added plus removed, or an untracked file's whole length.

        # Returns

        the count; None for a binary file, or an untracked one that cannot be
        read as text

        # Example

            >>> Change(Path("/r/a.rs"), "M", (3, 1)).lines(), Change(Path("/r/logo.png"), "M", None).lines()
            (4, None)
        """
        # --------------------------------------------------
        # git counted it: added plus removed
        # --------------------------------------------------
        if self.counts is not None:
            return sum(self.counts)
        # --------------------------------------------------
        # only an untracked file can still be counted, by reading it
        # --------------------------------------------------
        if self.status != UNTRACKED:
            return None
        try:
            # --------------------------------------------------
            # count the lines on disk; an unreadable or non-text file has none
            # --------------------------------------------------
            return len(read_text(self.path).splitlines())
        except (OSError, UnicodeDecodeError):
            return None


@dataclass(frozen=True)
class RepoTree:
    """the outermost repo around a directory and every submodule under it, outermost first."""

    repos: tuple[Path, ...]

    @classmethod
    def containing(cls, start: Path) -> "RepoTree":
        """the one repo whose work tree holds a directory, without its superproject or submodules.

        # Arguments

        * `start` - any directory inside the repo

        # Returns

        a tree of that repo's top alone; empty when `start` is not in a repo
        """
        # --------------------------------------------------
        # ask git for the checkout root
        # --------------------------------------------------
        top = git(start, "rev-parse", "--show-toplevel")
        return cls(() if top is None else (Path(top.removesuffix("\n")),))

    @classmethod
    def around(cls, start: Path) -> "RepoTree":
        """climb to the outermost superproject, then descend through every checked-out submodule.

        # Arguments

        * `start` - any directory inside the tree

        # Returns

        the tree, outermost repo first; empty when `start` is not in a repo,
        which is an answer, not an error

        # Raises

        RepoError when git finds the repo but cannot list its superproject or
        its submodules

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Path(tmp).resolve()
            ...     (repo / "my sub").mkdir()
            ...     for here in (repo, repo / "my sub"):
            ...         _ = git(here, "init", "-q")
            ...     _ = git(repo, "update-index", "--add", "--cacheinfo", f"{GITLINK_MODE},{'1' * 40},my sub")
            ...     tree = RepoTree.around(repo / "my sub")
            ...     [p.relative_to(repo).as_posix() for p in tree.repos]
            ['.', 'my sub']
        """
        # --------------------------------------------------
        # start from the checkout containing the path; none means no tree
        # --------------------------------------------------
        if not (found := list(cls.containing(start).repos)):
            return cls(())
        # --------------------------------------------------
        # climb to the outermost superproject
        # --------------------------------------------------
        while outer := cls.ask(found[0], "rev-parse", "--show-superproject-working-tree").strip():
            found = [Path(outer)]
        # --------------------------------------------------
        # descend through every submodule
        # --------------------------------------------------
        # breadth-first: each submodule found is searched in turn for its own
        for repo in found:
            found += [path for path in cls.gitlinks(repo) if cls.checked_out(path)]
        return cls(tuple(found))

    def changed(self) -> list[Path]:
        """every uncommitted path in every repo of the tree, untracked and deleted included.

        a repo with no commit has no HEAD to diff against, so everything it
        tracks is changed. a submodule's pointer in its parent is dropped: the
        submodule's own files say what changed

        # Returns

        absolute paths, each once

        # Raises

        RepoError when git cannot list a repo

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Path(tmp).resolve()
            ...     _ = git(repo, "init", "-q")
            ...     for name in ("staged.nix", "café menu.nix"):
            ...         _ = (repo / name).write_text("x")
            ...     _ = git(repo, "add", "staged.nix")
            ...     sorted(p.relative_to(repo).as_posix() for p in RepoTree((repo,)).changed())
            ['café menu.nix', 'staged.nix']
        """
        out: list[Path] = []
        for repo in self.repos:
            # --------------------------------------------------
            # a repo with no commit yet diffs against nothing, so every cached file is a change
            # --------------------------------------------------
            if git(repo, "rev-parse", "--verify", "-q", "HEAD") is None:
                out += self._names(repo, "ls-files", "-z", "--cached")
            else:
                out += self._names(repo, "diff", "-z", "--name-only", "HEAD")
            # --------------------------------------------------
            # untracked files that are not ignored
            # --------------------------------------------------
            out += self._names(repo, "ls-files", "-z", "--others", "--exclude-standard")
        # --------------------------------------------------
        # dedupe, preserving order, and leave out the repo roots themselves
        # --------------------------------------------------
        return [p for p in dict.fromkeys(out) if p not in self.repos]

    def since(self, ref: str) -> list[Change]:
        r"""every file the working tree changed since a ref, in each repo of the tree, untracked ones included.

        each repo is listed whole, whatever the cwd. renames are detected, and a
        renamed file is listed once, under its new name

        # Arguments

        * `ref` - a revision that resolves in every repo of the tree

        # Returns

        the tracked changes in git's order, then the untracked files

        # Raises

        RepoError when the ref does not resolve or git cannot list a repo

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Path(tmp).resolve()
            ...     _ = git(repo, "init", "-q")
            ...     _ = (repo / "kept.rs").write_text("a\nb\n")
            ...     _ = (repo / "moved.rs").write_text("x\n" * 20)
            ...     _ = git(repo, "add", ".")
            ...     _ = git(repo, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "base")
            ...     _ = (repo / "kept.rs").write_text("a\nc\n")
            ...     _ = git(repo, "mv", "moved.rs", "new name.rs")
            ...     _ = (repo / "fresh.rs").write_text("1\n2\n3\n")
            ...     [(c.path.name, c.status, c.counts, c.lines()) for c in RepoTree((repo,)).since("HEAD")]
            [('kept.rs', 'M', (1, 1), 2), ('new name.rs', 'R', (0, 0), 0), ('fresh.rs', '?', None, 3)]
        """
        out: list[Change] = []
        for repo in self.repos:
            # --------------------------------------------------
            # line counts for this repo's changes since the ref
            # --------------------------------------------------
            counts = self._numstat(repo, ref)
            # --------------------------------------------------
            # status and path of each change, renames included
            # --------------------------------------------------
            # each entry is `status`, then its path; a rename's status `R<score>` is followed by both names
            entries = iter(self.ask(repo, "diff", "-z", "--name-status", "--find-renames", "--end-of-options",
                                    ref, "--").split("\0"))
            for status in entries:
                name = next(entries, "")
                if status.startswith("R"):
                    name = next(entries, "")
                if name:
                    out.append(Change(repo / name, status[:1], counts.get(name)))
            # --------------------------------------------------
            # untracked files carry no counts
            # --------------------------------------------------
            out += [Change(path, UNTRACKED, None)
                    for path in self._names(repo, "ls-files", "-z", "--others", "--exclude-standard")]
        return out

    def tracked(self) -> list[Path]:
        """every file git tracks in every repo of the tree.

        # Returns

        absolute paths of regular files and symlinks, each once; a submodule's
        entry in its parent is a directory and a deleted file is gone, so both
        are dropped

        # Raises

        RepoError when git cannot list a repo
        """
        return self._present("ls-files", "-z", "--cached")

    def untracked(self) -> list[Path]:
        r"""every untracked, unignored file in every repo of the tree, shaped as `tracked` is.

        # Returns

        absolute paths of the files git does not track and does not ignore, each once

        # Raises

        RepoError when git cannot list a repo

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Path(tmp).resolve()
            ...     _ = git(repo, "init", "-q")
            ...     for name in (os.fsdecode(b"caf\xe9.nix"), "carriage\rreturn.nix"):
            ...         _ = (repo / name).write_text("x")
            ...     sorted(os.fsencode(p.name) for p in RepoTree((repo,)).untracked())
            [b'caf\xe9.nix', b'carriage\rreturn.nix']
        """
        return self._present("ls-files", "-z", "--others", "--exclude-standard")

    def without(self, root: Path) -> "RepoTree":
        """the repos whose resolved path is not at or under `root`'s.

        # Arguments

        * `root` - the directory whose repos, and any nested inside it, are dropped

        # Returns

        a tree of the remaining repos, in their original order

        # Example

            >>> RepoTree((Path("/r"), Path("/r/logs"))).without(Path("/r/logs")).repos
            (PosixPath('/r'),)
        """
        # --------------------------------------------------
        # drop every repo at or under the root
        # --------------------------------------------------
        bound = root.resolve()
        return RepoTree(tuple(repo for repo in self.repos if not repo.resolve().is_relative_to(bound)))

    @staticmethod
    def ask(repo: Path, *argv: str, timeout: float = GIT_TIMEOUT) -> str:
        """git's answer in a repo; a git that gave none raises, saying why.

        # Arguments

        * `repo` - the repository to run in
        * `argv` - the git subcommand and its arguments
        * `timeout` - seconds before the command counts as failed

        # Returns

        git's stdout, empty only when git ran and said nothing

        # Raises

        RepoError when git is missing, cannot start, runs past `timeout`, or exits non-zero

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     try:
            ...         RepoTree.ask(Path(tmp), "rev-parse", "HEAD")
            ...     except RepoError as error:
            ...         print(str(error).replace(tmp, "TMP"))
            `git rev-parse HEAD` in TMP exited 128
        """
        run = GitRun.of(repo, *argv, timeout=timeout)
        if not run.ok:
            raise RepoError(run)
        return run.stdout

    def _present(self, *argv: str) -> list[Path]:
        """one listing over every repo, kept to the regular files and symlinks on disk.

        # Arguments

        * `argv` - the git listing command, run in each repo; its output must be nul-separated

        # Returns

        absolute paths, each once
        """
        # --------------------------------------------------
        # every named path that exists as a file or symlink, not a deleted one
        # --------------------------------------------------
        listed = (path for repo in self.repos for path in self._names(repo, *argv))
        return [path for path in listed if path.is_symlink() or path.is_file()]

    @classmethod
    def _numstat(cls, repo: Path, ref: str) -> dict[str, tuple[int, int] | None]:
        """each changed name's (added, removed) lines since a ref; None for a binary file, which git counts as `-`.

        # Arguments

        * `repo` - the repository to count in
        * `ref` - the revision to count changes since

        # Returns

        the counts keyed by the file's path relative to the repo; a rename is
        keyed by its new name
        """
        out: dict[str, tuple[int, int] | None] = {}
        # --------------------------------------------------
        # split each numstat row, folding a rename's two names into one
        # --------------------------------------------------
        # each entry is `added<TAB>removed<TAB>path`; a rename leaves the path empty and gives both names after it
        rows = iter(cls.ask(repo, "diff", "-z", "--numstat", "--find-renames", "--end-of-options",
                            ref, "--").split("\0"))
        for row in rows:
            added, _, rest = row.partition("\t")
            removed, _, name = rest.partition("\t")
            if row and not name:
                _, name = next(rows, ""), next(rows, "")
            if name:
                out[name] = (int(added), int(removed)) if added.isdigit() and removed.isdigit() else None
        return out

    @classmethod
    def gitlinks(cls, repo: Path) -> list[Path]:
        """every submodule a repo's index holds, checked out or not.

        # Arguments

        * `repo` - the superproject whose index is read

        # Returns

        the absolute path of each submodule, each once, in index order

        # Raises

        RepoError when git cannot list the index
        """
        # --------------------------------------------------
        # every staged entry of the repo
        # --------------------------------------------------
        staged = cls.ask(repo, "ls-files", "-z", "--stage").split("\0")
        # --------------------------------------------------
        # keep the gitlinks
        # --------------------------------------------------
        # each entry is `mode sha stage<TAB>path`; an unmerged submodule is listed once per stage
        return list(dict.fromkeys(repo / path for meta, _, path in (e.partition("\t") for e in staged)
                                  if meta.split(" ", 1)[0] == GITLINK_MODE))

    @staticmethod
    def checked_out(submodule: Path) -> bool:
        """whether a submodule is checked out; git run in one that is not answers for its superproject.

        # Arguments

        * `submodule` - the submodule's path, as `gitlinks` lists it

        # Returns

        True when the submodule holds its `.git`, which one never initialised lacks
        """
        return (submodule / ".git").exists()

    @classmethod
    def _names(cls, repo: Path, *argv: str) -> list[Path]:
        """one nul-separated listing, as absolute paths under the repo, each once.

        # Arguments

        * `repo` - the repository to list in
        * `argv` - the git listing command, whose output is nul-separated

        # Returns

        the listed names joined onto the repo path, in git's order
        """
        return [repo / name for name in dict.fromkeys(cls.ask(repo, *argv).split("\0")) if name]
