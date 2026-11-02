"""brainlib.repos: what a git tree is - its repos, and the files each one lists.

a tree is the outermost repo around a directory and every submodule under it.
every listing asks git for nul-separated names, so a path holding a space, a
newline or a non-ascii character comes back as written, and a git that cannot
answer raises RepoError rather than reading as an empty repo

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.text import read_text
from brainlib.tool import NoVerdict
from brainlib.vocab import GIT_TIMEOUT

# --------------------------------------------------
# external
# --------------------------------------------------
import os
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# the mode git gives a submodule's entry in its parent's index
GITLINK_MODE = "160000"
# the status `RepoTree.since` gives a file git does not track
UNTRACKED = "?"


class RepoError(NoVerdict):
    """git could not answer about a repo; a caller never reads this as an empty answer."""

    def __init__(self, repo: Path, argv: Sequence[str]) -> None:
        """the repo and the git arguments that failed in it.

        # Arguments

        * `repo` - the repository the command was run in
        * `argv` - the git subcommand and arguments, as they were passed
        """
        super().__init__(f"git could not run `git {' '.join(argv)}` in {repo}")


def git(repo: Path, *argv: str) -> str | None:
    r"""run a git command in a repo and return its stdout.

    every git command the brain runs goes through here, but brain-sync's own
    writes (its `Repo.run`): those commit and push as him, stream their output
    to him, and wait on the network

    None and "" are different answers and the distinction is load-bearing: a
    caller that cannot tell "git said nothing" from "git could not run" reports
    a clean scan of a repo it never opened

    stdout is read as bytes and decoded the way the filesystem decodes a name
    (`os.fsdecode`), so a name that is not utf-8 maps back to the same path and
    a `\r` inside a name is not rewritten as a newline

    # Arguments

    * `repo` - the repository to run in
    * `argv` - the git subcommand and its arguments

    # Returns

    stdout on success; None when git is missing, the path is not a repo, or the
    command failed
    """
    # --------------------------------------------------
    # no git on the path means no answer
    # --------------------------------------------------
    found = shutil.which("git")
    if found is None:
        return None
    # --------------------------------------------------
    # strip the inherited git environment
    # --------------------------------------------------
    # GIT_DIR and GIT_WORK_TREE outrank -C, so an inherited environment would
    # silently measure a DIFFERENT repo than the one asked for
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    # --------------------------------------------------
    # run git in the repo; a failure to run or time out is no answer
    # --------------------------------------------------
    # argv is the caller's own literals plus a discovered repo path; nothing here
    # is remote input, and shell=False keeps it an exec not a shell (S603)
    try:
        done = subprocess.run([found, "-C", str(repo), *argv], capture_output=True,  # noqa: S603
                              check=False, env=env, timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    # --------------------------------------------------
    # only a clean exit yields output
    # --------------------------------------------------
    return os.fsdecode(done.stdout) if done.returncode == 0 else None


@dataclass(frozen=True)
class Change:
    """one file changed since a ref, as `RepoTree.since` lists it."""

    # absolute; a renamed file's new name
    path: Path
    # git's status letter (A, M, D, R, T, ...), or UNTRACKED
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
        while outer := cls._ask(found[0], "rev-parse", "--show-superproject-working-tree").strip():
            found = [Path(outer)]
        # --------------------------------------------------
        # descend through every submodule
        # --------------------------------------------------
        # breadth-first: each submodule found is searched in turn for its own
        for repo in found:
            found += cls._gitlinks(repo)
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
            entries = iter(self._ask(repo, "diff", "-z", "--name-status", "--find-renames", ref, "--").split("\0"))
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
        rows = iter(cls._ask(repo, "diff", "-z", "--numstat", "--find-renames", ref, "--").split("\0"))
        for row in rows:
            added, _, rest = row.partition("\t")
            removed, _, name = rest.partition("\t")
            if row and not name:
                _, name = next(rows, ""), next(rows, "")
            if name:
                out[name] = (int(added), int(removed)) if added.isdigit() and removed.isdigit() else None
        return out

    @classmethod
    def _gitlinks(cls, repo: Path) -> list[Path]:
        """the checked-out submodules a repo's index holds; one never initialised has no `.git`.

        # Arguments

        * `repo` - the superproject whose index is read

        # Returns

        the absolute path of each submodule that is checked out
        """
        # --------------------------------------------------
        # every staged entry of the repo
        # --------------------------------------------------
        staged = cls._ask(repo, "ls-files", "-z", "--stage").split("\0")
        # --------------------------------------------------
        # keep the gitlinks that are checked out
        # --------------------------------------------------
        # each entry is `mode sha stage<TAB>path`; an unmerged submodule is listed once per stage
        linked = dict.fromkeys(repo / path for meta, _, path in (e.partition("\t") for e in staged)
                               if meta.split(" ", 1)[0] == GITLINK_MODE)
        return [path for path in linked if (path / ".git").exists()]

    @classmethod
    def _names(cls, repo: Path, *argv: str) -> list[Path]:
        """one nul-separated listing, as absolute paths under the repo, each once.

        # Arguments

        * `repo` - the repository to list in
        * `argv` - the git listing command, whose output is nul-separated

        # Returns

        the listed names joined onto the repo path, in git's order
        """
        return [repo / name for name in dict.fromkeys(cls._ask(repo, *argv).split("\0")) if name]

    @staticmethod
    def _ask(repo: Path, *argv: str) -> str:
        """git's answer in a repo; a failure raises rather than reading as an empty one.

        # Arguments

        * `repo` - the repository to run in
        * `argv` - the git subcommand and its arguments

        # Returns

        git's stdout, empty only when git ran and said nothing

        # Raises

        RepoError when git is missing or the command failed
        """
        # --------------------------------------------------
        # a git that did not run is an error here, not an empty answer
        # --------------------------------------------------
        answer = git(repo, *argv)
        if answer is None:
            raise RepoError(repo, argv)
        return answer
