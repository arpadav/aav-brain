#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-sync: push the brain's repos to main, innermost first.

the repos are discovered, never hardcoded (P32): the brain's own submodules
(e.g. logs), the brain store, then the superproject that holds it (the
home-manager repo). inner goes first so the outer one commits the inner one's
new pointer.

a repo already even with origin main is left alone. any other repo carries its
work to main through a short-lived local branch, `brain-sync`:

    1. cut `brain-sync` from HEAD - main, a detached submodule checkout, anything
    2. commit everything on it as arpadav, message `brain-sync`
    3. fetch origin main and merge it, then local main, into the branch
    4. switch to main and fast-forward it to the branch
    5. push main to origin and delete the branch

a merge that conflicts stops on the branch with the merge in progress and exits
CONFLICT; once the caller stages the resolution, running this again commits it
and resumes at step 3. a push refused because origin moved in the meantime goes
back to step 3, up to PUSH_ATTEMPTS times. the branch is never pushed.

    python3 brain-sync.py           # sync all
    python3 brain-sync.py --check   # print each repo's state, change nothing

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Exit, Flag, find_brain, git

# --------------------------------------------------
# external
# --------------------------------------------------
import os
import shutil
import subprocess
from dataclasses import dataclass, field

# --------------------------------------------------
# constants
# --------------------------------------------------
TOOL = Path(__file__).stem
AUTHOR_NAME = "arpadav"
AUTHOR_EMAIL = "arpadav@gmail.com"
MESSAGE = "brain-sync"
REMOTE = "origin"
BRANCH = "main"
# local only; it exists while a sync is in flight and is deleted once main is pushed
SYNC_BRANCH = "brain-sync"
# rounds of merge-and-push before a repo whose origin keeps moving is given up on
PUSH_ATTEMPTS = 3
# a push or fetch over the network; generous, but never forever
NETWORK_TIMEOUT_S = 300


class SyncError(Exception):
    """a repo cannot reach origin main without the caller stepping in."""

    def __init__(self, repo: Path, reason: str) -> None:
        """the repo that stopped, and why."""
        super().__init__(f"{repo}: {reason}")
        self.repo: Path = repo


class ConflictError(SyncError):
    """a merge in a repo stopped on conflicting files."""

    def __init__(self, repo: Path, files: list[str]) -> None:
        """the repo the merge is in, and its unmerged files."""
        super().__init__(repo, f"{len(files)} conflicting file(s)")
        self.files: list[str] = files


@dataclass(frozen=True)
class Repo:
    """one git work tree that syncs to origin main."""

    path: Path

    def run(self, *argv: str) -> bool:
        """run a mutating git command as arpadav, echoing it (P59); whether it succeeded.

        the read-only counterpart is brainlib's `git`. this one commits and
        pushes, so it carries the identity and shows the command
        """
        found = shutil.which("git")
        if found is None:
            return False
        print(f"+ git -C {self.path} {' '.join(argv)}", file=sys.stderr)
        # GIT_DIR and GIT_WORK_TREE outrank -C, as in brainlib's `git`
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        identity = ("-c", f"user.name={AUTHOR_NAME}", "-c", f"user.email={AUTHOR_EMAIL}")
        # argv is this tool's own literals plus a discovered repo path; no shell (S603)
        done = subprocess.run([found, *identity, "-C", str(self.path), *argv],  # noqa: S603
                              check=False, env=env, timeout=NETWORK_TIMEOUT_S)
        return done.returncode == 0

    def read(self, *argv: str) -> str:
        """stdout of a read-only git command; empty when git said nothing or could not run."""
        return (git(self.path, *argv) or "").strip()

    def merging(self) -> bool:
        """whether a merge is in progress."""
        return git(self.path, "rev-parse", "-q", "--verify", "MERGE_HEAD") is not None

    def conflicts(self) -> list[str]:
        """the files still unmerged."""
        return self.read("diff", "--name-only", "--diff-filter=U").splitlines()

    def has_branch(self, name: str) -> bool:
        """whether a local branch exists."""
        return git(self.path, "rev-parse", "-q", "--verify", f"refs/heads/{name}") is not None

    def fetch(self) -> None:
        """fetch origin main into FETCH_HEAD."""
        if not self.run("fetch", REMOTE, BRANCH):
            raise SyncError(self.path, f"cannot fetch {REMOTE}/{BRANCH}")

    def merge(self, ref: str) -> None:
        """merge a ref into HEAD as `brain-sync`; a stop leaves the merge in progress."""
        if not self.run("merge", "--no-edit", "-m", MESSAGE, ref):
            raise ConflictError(self.path, self.conflicts())

    def even(self) -> bool:
        """on main, nothing uncommitted, and at the commit just fetched."""
        return (self.read("branch", "--show-current") == BRANCH
                and not self.read("status", "--porcelain")
                and self.read("rev-parse", "HEAD") == self.read("rev-parse", "FETCH_HEAD"))

    def sync(self) -> None:
        """carry this repo's work to origin main through SYNC_BRANCH (the module doc's steps)."""
        # --------------------------------------------------
        # a merge the caller resolved
        # --------------------------------------------------
        if self.merging():
            if unmerged := self.conflicts():
                raise ConflictError(self.path, unmerged)
            self.run("commit", "--no-edit", "-m", MESSAGE)
        # --------------------------------------------------
        # nothing to carry
        # --------------------------------------------------
        self.fetch()
        if self.even():
            return
        # --------------------------------------------------
        # the work, committed on its own branch
        # --------------------------------------------------
        if self.read("branch", "--show-current") != SYNC_BRANCH and not self.run("switch", "-c", SYNC_BRANCH):
            raise SyncError(self.path, f"branch {SYNC_BRANCH} exists but is not checked out; "
                                       f"switch to it to resume, or delete it")
        self.run("add", "-A")
        if self.read("diff", "--cached", "--name-only"):
            self.run("commit", "-m", MESSAGE)
        # --------------------------------------------------
        # main into the branch, the branch back into main
        # --------------------------------------------------
        for _ in range(PUSH_ATTEMPTS):
            self.merge("FETCH_HEAD")
            if self.has_branch(BRANCH):
                self.merge(BRANCH)
            if not (self.run("switch", BRANCH) and self.run("merge", "--ff-only", SYNC_BRANCH)):
                raise SyncError(self.path, f"{BRANCH} would not fast-forward to {SYNC_BRANCH}")
            if self.run("push", REMOTE, f"{BRANCH}:{BRANCH}"):
                self.run("branch", "-d", SYNC_BRANCH)
                return
            # --------------------------------------------------
            # origin moved since the fetch; merge it again
            # --------------------------------------------------
            self.run("switch", SYNC_BRANCH)
            self.fetch()
        raise SyncError(self.path, f"{REMOTE} refused {PUSH_ATTEMPTS} pushes of {BRANCH}")


@dataclass(frozen=True)
class Sync:
    """the brain's repos in push order: submodules, the store, its superproject."""

    repos: list[Repo] = field(default_factory=list)

    @classmethod
    def discover(cls, brain: Path) -> "Sync":
        """the repos around one brain store."""
        store = Repo(brain)
        inner = [Repo(brain / line.split()[1]) for line in store.read("submodule", "status").splitlines()]
        outer = store.read("rev-parse", "--show-superproject-working-tree")
        return cls([*inner, store, *([Repo(Path(outer))] if outer else [])])

    def check(self) -> Exit:
        """print each repo's state; change nothing."""
        for repo in self.repos:
            print(f"{repo.path}\n{repo.read('status', '-sb')}\n")
        return Exit.OK

    def push(self) -> Exit:
        """sync every repo innermost first; stop at the first one that cannot reach main."""
        for repo in self.repos:
            try:
                repo.sync()
            except ConflictError as conflict:
                print(f"{TOOL}: merge conflict in {conflict.repo}", file=sys.stderr)
                print("\n".join(f"  {name}" for name in conflict.files), file=sys.stderr)
                return Exit.CONFLICT
            except SyncError as blocked:
                print(f"{TOOL}: {blocked}", file=sys.stderr)
                return Exit.BLOCKED
            print(f"{TOOL}: {repo.path} synced to {REMOTE}/{BRANCH}")
        return Exit.OK


def main() -> None:
    """parse the one flag and sync."""
    args = Args.from_argv()
    if unknown := args.unknown(Flag.CHECK):
        sys.exit(f"{TOOL}: unknown flag {unknown[0]}")
    sync = Sync.discover(find_brain())
    sys.exit(sync.check() if args.has(Flag.CHECK) else sync.push())


if __name__ == "__main__":
    main()
