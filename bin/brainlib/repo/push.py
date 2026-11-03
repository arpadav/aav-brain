"""brainlib.repo.push: what a push publishes, as excerpts of text that each know where they sit.

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib.repo.diff import Patch
from brainlib.repo.tree import RepoError, RepoTree
from brainlib.vocab import GIT_TIMEOUT, LONG_GIT_TIMEOUT, NoVerdict, UsageError

# --------------------------------------------------
# external
# --------------------------------------------------
from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import ClassVar

# --------------------------------------------------
# constants
# --------------------------------------------------
# the history a push sends, never a `git replace` stand-in for it
NO_REPLACE = "--no-replace-objects"
# what opens each commit of PATCH_LOG's output (its `%x00`); a diff row never starts with a nul
COMMIT_MARK = "\0"
# the patch log: every commit's patch as text, the root commit's included, merges as what their
# resolution changed, no signature check; each commit opens with COMMIT_MARK and its full id
PATCH_LOG = ("log", "-p", "--root", "--text", "--no-show-signature", "--diff-merges=remerge", "--format=%x00%H")


@dataclass(frozen=True)
class Origin:
    """where one line a push would publish sits: its repo, the commit holding it, its path, its 1-based line."""

    repo: Path
    # a path relative to the repo: in the work tree (an editor opens it) or as `commit` holds it
    # (`git show <commit>:<path>` opens it); "" for the commit object itself (`git cat-file -p <commit>`)
    name: str
    line: int
    # the full id of the commit the text is in; None for the work tree
    commit: str | None = None
    # the leading hex digits of `commit` a printed origin shows; every read takes the full id
    SHORT_ID: ClassVar[int] = 12

    def __str__(self) -> str:
        """`[commit:]name:line`, the location an editor or git jumps to, the commit id abbreviated.

        # Returns

        the abbreviated commit, the path and the line, colon-joined, each one present

        # Example

            >>> commit = "ab12cd34ef56" * 3 + "7890"
            >>> print(Origin(Path("/r"), "hosts.nix", 4), Origin(Path("/r"), "hosts.nix", 4, commit))
            hosts.nix:4 ab12cd34ef56:hosts.nix:4
            >>> print(Origin(Path("/r"), "", 6, commit))
            ab12cd34ef56:6
        """
        held = f"{self.commit[:self.SHORT_ID]}:" if self.commit else ""
        return f"{held}{self.name}:{self.line}" if self.name else f"{held}{self.line}"


@dataclass(frozen=True)
class Excerpt:
    """text a push would publish, its first line at `origin`."""

    origin: Origin
    text: str


@dataclass(frozen=True)
class Outgoing:
    """what a push of `tip` over `base` sends from one repo: each commit's raw object and the lines its patch adds."""

    # zero or one repo: a base resolves per repo
    tree: RepoTree
    base: str
    # the commit the push sends; HEAD unless the pusher resolved it first
    tip: str = "HEAD"
    # what the excerpts leave out, stated after every scan of them
    unread: ClassVar[str] = ("the working tree, the index, commits the base already holds, file names, tags, "
                             "and values this machine no longer holds")

    def __post_init__(self) -> None:
        """refuse a tree of more than one repo, since one base cannot name a commit in each.

        # Raises

        UsageError when the tree holds more than one repo
        """
        if len(self.tree.repos) > 1:
            raise UsageError(f"a base resolves per repo, so name one repo; this tree holds {len(self.tree.repos)}")

    @property
    def span(self) -> str:
        """the commits the tip reaches and the base does not, as git spells the range.

        # Returns

        `<base>..<tip>`
        """
        return f"{self.base}..{self.tip}"

    def resolved(self) -> "Outgoing":
        """the same push with its base and tip resolved to full commit ids, before anything is read.

        # Returns

        a copy whose ends are commit ids; itself for a tree of no repo

        # Raises

        NoVerdict when the base or the tip does not resolve to a commit

        # Example

            >>> import tempfile
            >>> from brainlib.repo.tree import git
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Path(tmp).resolve()
            ...     _ = git(repo, "init", "-q")
            ...     who = ("-c", "user.name=t", "-c", "user.email=t@example.com")
            ...     _ = git(repo, *who, "commit", "-q", "--allow-empty", "-m", "b")
            ...     try:
            ...         Outgoing(RepoTree((repo,)), "nope").resolved()
            ...     except NoVerdict as wrong:
            ...         print(str(wrong).replace(str(repo), "REPO"))
            ...     ends = Outgoing(RepoTree((repo,)), "HEAD").resolved()
            ...     ends.base == ends.tip, len(ends.tip)
            nope does not resolve to a commit in REPO
            (True, 40)
        """
        if not self.tree.repos:
            return self
        repo = self.tree.repos[0]
        return replace(self, base=self._commit(repo, self.base), tip=self._commit(repo, self.tip))

    def covers(self) -> list[str]:
        """what the excerpts cover, one line; nothing is read.

        # Returns

        the range and how many repos it is read in
        """
        line = (
            f"every commit {self.tip} reaches and {self.base} does not, in {len(self.tree.repos)} repo(s): "
            "its raw object and the lines its patch adds"
        )
        return [line]

    def excerpts(self) -> Iterator[Excerpt]:
        r"""per repo, each commit's raw object, then each line the commits' patches add.

        the raw object (`git cat-file commit`) is what the push sends: the
        author and committer as stored, never as a .mailmap rewrites them, a
        merged signed tag's `mergetag`, a `gpgsig`, an `encoding`, and the
        message, numbered as `git cat-file -p` prints it. a merge adds only
        what its resolution changed: each parent's commits are read themselves,
        or are already behind the base. a commit an origin rewrite dropped is
        read again once a merge brings it back

        # Returns

        the excerpts, newest commit first, each patch's lines in its order

        # Raises

        NoVerdict when the range holds a merge of more than two parents, which
        has no resolution git can show; RepoError when an end does not resolve
        (`resolved` names which) or git cannot read the repo

        # Example

            >>> import tempfile
            >>> from brainlib.repo.tree import git
            >>> who = ("-c", "user.name=t", "-c", "user.email=t@example.com")
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Path(tmp).resolve()
            ...     _ = git(repo, "init", "-q", "-b", "main")
            ...     _ = (repo / "my f").write_text("a\nb\n")
            ...     _ = git(repo, "add", "my f")
            ...     _ = git(repo, *who, "commit", "-qm", "base")
            ...     _ = git(repo, "switch", "-qc", "side")
            ...     _ = (repo / "my f").write_text("a\nnew\nb\n")
            ...     _ = git(repo, *who, "commit", "-qam", "side")
            ...     _ = git(repo, "switch", "-q", "main")
            ...     _ = git(repo, *who, "merge", "-q", "--no-ff", "--no-commit", "side")
            ...     _ = (repo / "my f").write_text("a\nnew\nb\nresolved\n")
            ...     _ = git(repo, *who, "commit", "-qam", "merge")
            ...     out = list(Outgoing(RepoTree((repo,)), "main~1").excerpts())
            ...     sorted((f"{x.origin.name}:{x.origin.line}", x.text) for x in out if x.origin.name)
            ...     [x.text.splitlines()[-1] for x in out if not x.origin.name]
            ...     {len(x.origin.commit or "") for x in out}
            [('my f:2', 'new'), ('my f:4', 'resolved')]
            ['merge', 'side']
            {40}
        """
        for repo in self.tree.repos:
            for commit in self._commits(repo):
                yield Excerpt(Origin(repo, "", 1, commit), self._ask(repo, "cat-file", "commit", commit))
            yield from self._patches(repo)

    def _commits(self, repo: Path) -> list[str]:
        """the commits of the span in one repo, as full ids, newest first.

        a full id is read as the object it names; an abbreviated one is read as
        any branch or tag spelled the same, ahead of the commit

        # Arguments

        * `repo` - the repository to list in

        # Returns

        each commit the tip reaches and the base does not

        # Raises

        NoVerdict when a commit of the span merges more than two parents;
        RepoError when an end of the span does not resolve
        """
        # --------------------------------------------------
        # each commit with its parents; a row past three fields is an octopus merge
        # --------------------------------------------------
        rows = [row.split() for row in self._ask(repo, "rev-list", "--parents", "--end-of-options",
                                                 self.span).splitlines()]
        if octopus := [row[0] for row in rows if len(row) > 3]:  # noqa: PLR2004 - a commit and two parents
            raise NoVerdict(f"{repo}: {' '.join(octopus)} merge more than two parents, whose additions git "
                            f"cannot show; no verdict on {self.span}")
        return [row[0] for row in rows]

    def _patches(self, repo: Path) -> Iterator[Excerpt]:
        r"""each line the span's patches add in one repo, at its commit's full id and its path.

        the log is split where a row opens with COMMIT_MARK, never on a bare
        nul: `--text` can put a nul inside a file's line, but every hunk row
        opens with its prefix

        # Arguments

        * `repo` - the repository to read

        # Returns

        one excerpt per added row, newest commit first
        """
        log = self._ask(repo, *Patch.CONFIG, *PATCH_LOG, *Patch.ARGS, "--end-of-options", self.span, "--",
                        timeout=LONG_GIT_TIMEOUT)
        for chunk in f"\n{log}".split(f"\n{COMMIT_MARK}")[1:]:
            commit, _, body = chunk.partition("\n")
            for name, line, text in Patch.added(body):
                yield Excerpt(Origin(repo, name, line, commit), text)

    @classmethod
    def _commit(cls, repo: Path, ref: str) -> str:
        """one end of the span as a full commit id.

        # Arguments

        * `repo` - the repository to resolve in
        * `ref` - the revision, as the caller named it

        # Returns

        the commit id

        # Raises

        NoVerdict when the revision does not resolve to a commit
        """
        try:
            return cls._ask(repo, "rev-parse", "--verify", "-q", "--end-of-options", f"{ref}^{{commit}}").strip()
        except RepoError as unresolved:
            raise NoVerdict(f"{ref} does not resolve to a commit in {repo}") from unresolved

    @staticmethod
    def _ask(repo: Path, *argv: str, timeout: float = GIT_TIMEOUT) -> str:
        """git's answer about the history a push sends, never a `git replace` stand-in for it.

        # Arguments

        * `repo` - the repository to run in
        * `argv` - the git subcommand and its arguments
        * `timeout` - seconds before the command counts as failed

        # Returns

        git's stdout

        # Raises

        RepoError when git gives no answer
        """
        return RepoTree.ask(repo, NO_REPLACE, *argv, timeout=timeout)
