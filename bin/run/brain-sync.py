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

before anything in a repo is committed, brain-private scans that repo as
`git add -A` would stage it (P61); a scan that does not pass stops that repo's
sync with nothing staged.

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
from brainlib import Args, Exit, Flag, Layout, Tool, find_brain, git

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
# the git identity every commit is made under
AUTHOR_NAME = "arpadav"
AUTHOR_EMAIL = "arpadav@gmail.com"
# the message on every commit and merge commit this tool makes
MESSAGE = "brain-sync"
# the remote and the branch every repo is carried to
REMOTE = "origin"
BRANCH = "main"
# local only; it exists while a sync is in flight and is deleted once main is pushed
SYNC_BRANCH = "brain-sync"
# rounds of merge-and-push before a repo whose origin keeps moving is given up on
PUSH_ATTEMPTS = 3
# a push or fetch over the network; generous, but never forever
NETWORK_TIMEOUT_S = 300
# the scan every repo passes before anything in it is committed
PRIVATE_SCAN = (sys.executable, str(Layout.discover().private_script))


class SyncError(Exception):
    """a repo cannot reach origin main without the caller stepping in."""

    def __init__(self, repo: Path, reason: str) -> None:
        """the repo that stopped, and why.

        # Arguments

        * `repo` - the work tree that cannot reach origin main
        * `reason` - what stopped it, worded for the caller to act on
        """
        super().__init__(f"{repo}: {reason}")
        self.repo: Path = repo


class ConflictError(SyncError):
    """a merge in a repo stopped on conflicting files."""

    def __init__(self, repo: Path, files: list[str]) -> None:
        """the repo the merge is in, and its unmerged files.

        # Arguments

        * `repo` - the work tree whose merge stopped
        * `files` - the paths still unmerged, relative to the repo
        """
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

        # Arguments

        * `argv` - the git subcommand and its arguments

        # Returns

        True when git exited 0; False when it exited otherwise or is not installed
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
        """stdout of a read-only git command; empty when git said nothing or could not run.

        # Arguments

        * `argv` - the git subcommand and its arguments

        # Returns

        stdout with surrounding whitespace stripped
        """
        return (git(self.path, *argv) or "").strip()

    def scan(self) -> None:
        """run brain-private over this repo alone, as `git add -A` would stage it, echoing it (P59).

        judged by its exit code alone: a hit, an unscanned file and a scan
        that could not run all stop the sync
        """
        argv = (*PRIVATE_SCAN, Flag.STAGING, str(self.path))
        print(f"+ {' '.join(argv)}", file=sys.stderr)
        # the scan is this brain's own script under this interpreter; no shell (S603)
        done = subprocess.run(argv, check=False)  # noqa: S603
        if done.returncode != Exit.OK:
            raise SyncError(self.path, f"the private scan exited {done.returncode}; nothing is staged")

    def merging(self) -> bool:
        """whether a merge is in progress.

        # Returns

        True while the repo has a `MERGE_HEAD`, which a stopped merge leaves behind
        """
        return git(self.path, "rev-parse", "-q", "--verify", "MERGE_HEAD") is not None

    def conflicts(self) -> list[str]:
        """the files still unmerged.

        # Returns

        paths relative to the repo; empty when the merge left none
        """
        return self.read("diff", "--name-only", "--diff-filter=U").splitlines()

    def has_branch(self, name: str) -> bool:
        """whether a local branch exists.

        # Arguments

        * `name` - the branch name, without `refs/heads/`

        # Returns

        True when the branch is present locally
        """
        return git(self.path, "rev-parse", "-q", "--verify", f"refs/heads/{name}") is not None

    def fetch(self) -> None:
        """fetch origin main into FETCH_HEAD."""
        if not self.run("fetch", REMOTE, BRANCH):
            raise SyncError(self.path, f"cannot fetch {REMOTE}/{BRANCH}")

    def merge(self, ref: str) -> None:
        """merge a ref into HEAD as `brain-sync`; a stop leaves the merge in progress.

        # Arguments

        * `ref` - the revision to merge in

        # Raises

        ConflictError when the merge stops, carrying the unmerged files
        """
        if not self.run("merge", "--no-edit", "-m", MESSAGE, ref):
            raise ConflictError(self.path, self.conflicts())

    def even(self) -> bool:
        """on main, nothing uncommitted, and at the commit just fetched.

        # Returns

        True when the repo has nothing to carry to origin main
        """
        return (self.read("branch", "--show-current") == BRANCH
                and not self.read("status", "--porcelain")
                and self.read("rev-parse", "HEAD") == self.read("rev-parse", "FETCH_HEAD"))

    def sync(self) -> None:
        """carry this repo's work to origin main through SYNC_BRANCH (the module doc's steps).

        the private scan runs first, so nothing private reaches a commit. a repo
        already even with origin main returns after the fetch. a push refused
        because origin moved loops back to the merge, up to PUSH_ATTEMPTS rounds

        # Raises

        ConflictError when a merge stops on conflicting files, leaving it in
        progress for the caller to resolve; SyncError when the private scan
        fails, origin cannot be fetched, main will not fast-forward, or every
        push is refused
        """
        # --------------------------------------------------
        # nothing private goes into a commit
        # --------------------------------------------------
        self.scan()
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
        """the repos around one brain store.

        # Arguments

        * `brain` - the brain store's work tree

        # Returns

        the store's submodules, then the store, then the superproject that holds it, if any
        """
        store = Repo(brain)
        # not RepoTree: push order wants the store's own submodules and its DIRECT superproject only
        inner = [Repo(brain / line.split()[1]) for line in store.read("submodule", "status").splitlines()]
        outer = store.read("rev-parse", "--show-superproject-working-tree")
        return cls([*inner, store, *([Repo(Path(outer))] if outer else [])])

    def check(self) -> Exit:
        """print each repo's state; change nothing.

        # Returns

        `Exit.OK`
        """
        for repo in self.repos:
            print(f"{repo.path}\n{repo.read('status', '-sb')}\n")
        return Exit.OK

    def push(self) -> Exit:
        """sync every repo innermost first; stop at the first one that cannot reach main.

        # Returns

        `Exit.OK` when every repo synced; `Exit.CONFLICT` when a merge stopped on
        conflicts; `Exit.BLOCKED` when a repo could not be fetched, fast-forwarded or pushed
        """
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


def main(args: Args) -> Exit:
    """print each repo's state under --check, else sync.

    # Arguments

    * `args` - the parsed command line; `--check` prints state and changes nothing

    # Returns

    `Exit.OK` when every repo reached origin main (or `--check` ran),
    `Exit.CONFLICT` when a merge stopped on conflicts, `Exit.BLOCKED` when a repo
    could not reach origin main
    """
    sync = Sync.discover(find_brain())
    return sync.check() if args.has(Flag.CHECK) else sync.push()


if __name__ == "__main__":
    Tool(TOOL, __doc__, flags=(Flag.CHECK,)).run(main)
