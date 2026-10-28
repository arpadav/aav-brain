#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-sync: push the brain's repos to main, innermost first.

the repos are discovered, never hardcoded (P32): the brain's own submodules
(e.g. logs), the brain store, then the superproject that holds it (the
home-manager repo). each commits everything it has as arpadav, message
`brain-sync`, and pushes to origin main. inner goes first so the outer one
commits the inner one's new pointer.

a rejected push fetches and merges origin/main (message `brain-sync`) and
pushes again. a merge that conflicts stops, leaves the merge in progress and
exits CONFLICT; once the caller stages the resolution, running this again
finishes the merge and continues.

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
# a push or fetch over the network; generous, but never forever
NETWORK_TIMEOUT_S = 300


class ConflictError(Exception):
    """a merge in a repo stopped on conflicting files."""

    def __init__(self, repo: Path, files: list[str]) -> None:
        """the repo the merge is in, and its unmerged files."""
        super().__init__(f"{repo}: {len(files)} conflicting file(s)")
        self.repo: Path = repo
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

    def sync(self) -> None:
        """commit everything and push to main; on rejection merge origin/main and push again."""
        # --------------------------------------------------
        # a merge the caller resolved
        # --------------------------------------------------
        if self.merging():
            if unmerged := self.conflicts():
                raise ConflictError(self.path, unmerged)
            self.run("commit", "--no-edit", "-m", MESSAGE)
        # --------------------------------------------------
        # commit what is here
        # --------------------------------------------------
        self.run("add", "-A")
        if self.read("diff", "--cached", "--name-only"):
            self.run("commit", "-m", MESSAGE)
        # --------------------------------------------------
        # push; a rejection merges origin/main once
        # --------------------------------------------------
        if self.run("push", REMOTE, f"HEAD:{BRANCH}"):
            return
        self.run("fetch", REMOTE, BRANCH)
        if not self.run("merge", "--no-edit", "-m", MESSAGE, "FETCH_HEAD"):
            raise ConflictError(self.path, self.conflicts())
        if not self.run("push", REMOTE, f"HEAD:{BRANCH}"):
            raise ConflictError(self.path, [])


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
        """sync every repo innermost first; CONFLICT stops at the first conflicted one."""
        for repo in self.repos:
            try:
                repo.sync()
            except ConflictError as conflict:
                print(f"{TOOL}: merge conflict in {conflict.repo}", file=sys.stderr)
                print("\n".join(f"  {name}" for name in conflict.files), file=sys.stderr)
                return Exit.CONFLICT
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
