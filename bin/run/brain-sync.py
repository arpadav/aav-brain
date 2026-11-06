#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""b-sync: push the edit copy's repos to main, innermost first, then bring them into the install copy.

the repos are those of the edit copy's brain (`XdgLayout.edit_brain()`),
whichever copy this script runs from, discovered, never hardcoded (P32): its
checked-out submodules (e.g. logs), the brain store, then the superproject
that holds it (the home repo). inner goes first so the outer one commits the
inner one's new pointer. a submodule this clone never checked out is not
synced - git run there answers for the store - and is named in a warning
instead. once every repo is pushed, `sy` pulls origin into the install copy
and switches it.

b-private's scan guards both ends (P61), run in this process with the
values probed once per run, at the first scan: before anything in a repo is
committed it scans the repo's work tree, and before the push it scans
exactly the commits the push sends. what each scan reads, what
it leaves unread and which repo it exempts is b-private's to say:
`b-private -h`.

each repo goes through these steps in order. BASE and TIP are commit ids,
each resolved once, and every later step takes the id; local main is merged
by its full ref, which no tag can shadow. a step that stages takes everything
but the repo's top-level `plans/`, his per-machine scratch and open items, so
nothing there is committed even in a repo whose .gitignore lacks the rule:

    1. check origin fetches from one url and pushes to that url, fetch
       origin's main into a ref only b-sync writes, and resolve it to BASE
    2. on main, nothing staged or to stage, at BASE, no `brain-sync` branch
       and no learner worktree: nothing to carry, so nothing is scanned
    3. every learner worktree - one other than the main worktree, checked
       out on a `learn/*` branch (brain-learner) - must be unlocked, since a
       learner locks its worktree while it runs, and hold nothing
       uncommitted; one whose directory was deleted holds nothing, and its
       branch is folded all the same; then scan the work tree, as
       `b-private REPO` does
    4. a merge resolved on `brain-sync`: stage everything, as step 3 scanned
       it, and commit
    5. cut `brain-sync` from HEAD - main, a detached submodule checkout,
       anything - and commit everything on it; then merge each learner's
       branch into it, remove its worktree - or prune the record of one
       whose directory was deleted - and delete the branch, so main holds
       the learner's commits at step 9
    6. merge BASE, then local main when there is one, into it, and resolve
       its tip to TIP
    7. scan the commits TIP reaches and BASE does not
    8. push TIP to origin's main, tags and submodules off; a push refused as
       not a fast-forward fetches a new BASE and goes back to 6, until the
       `moved` stop below
    9. fast-forward main to TIP, or make it at TIP when there is none, and
       delete `brain-sync`

every commit and merge commit is made as arpadav, message `brain-sync`. main
moves only at step 9, once origin accepted TIP, and no `brain-sync` branch is
ever made on origin. a repo that cannot go on is a stop, listed below; once
its cause is dealt with, running b-sync again resumes. apart from a stop,
a wrong command line exits 2, and a crash, or no edit copy, exits 1.

after the last repo, b-sync prints `Running: sy` and runs it; sy missing or
failing is the `apply` stop, every push already made.

the warnings - no private.toml, a submodule not checked out - are the first
lines printed and the last, after a stop too; the exit is unchanged by them.

    b-sync     # sync all
    b-sync -c  # print each repo's state and learner worktrees, change nothing

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import (
    LONG_GIT_TIMEOUT,
    NO_REPLACE,
    PLANS,
    Args,
    Ending,
    Exit,
    Flag,
    GitRun,
    Layout,
    NoVerdict,
    PrivateScan,
    RepoError,
    RepoTree,
    ScanScope,
    Tool,
    XdgLayout,
)

# --------------------------------------------------
# external
# --------------------------------------------------
import shlex
import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages
TOOL = Layout.command(Path(__file__))
# the git identity every commit and merge commit is made under, pinned per role: an `author.*`
# or `committer.*` in his config outranks `user.*`, even a `user.*` given with `-c`
AUTHOR_NAME = "arpadav"
AUTHOR_EMAIL = "arpadav@gmail.com"
IDENTITY = tuple(arg for role in ("author", "committer")
                 for arg in ("-c", f"{role}.name={AUTHOR_NAME}", "-c", f"{role}.email={AUTHOR_EMAIL}"))
# the message on every commit and merge commit this tool makes
MESSAGE = "brain-sync"
# every path of the repo but what is under its top-level plans/, as a pathspec: what steps 2, 4
# and 5 stage. the first letter is bracketed because `git add` fails on an ignored path that an
# exclusion spells out literally, and a bracket is a wildcard it does not compare
UNPLANNED = ("--", ":(top)", f":(top,exclude,glob)[{PLANS[0]}]{PLANS[1:]}/**")
# the remote every repo is carried to
REMOTE = "origin"
# the branch every repo is carried to, by name (switch) and as the one ref it is (fetch, merge, push)
MAIN = "main"
MAIN_REF = f"refs/heads/{MAIN}"
# local only: cut at step 5, deleted at step 9 once local main holds what origin accepted
SYNC_BRANCH = "brain-sync"
# the branches a learner's worktree is cut on (brain-learner), each merged into SYNC_BRANCH and deleted at step 5
LEARNER_PREFIX = "refs/heads/learn/"
# rounds of merge-and-push before a repo whose origin keeps moving is given up on
PUSH_ATTEMPTS = 3
# where each fetch force-writes origin's main, resolved to BASE once per fetch: no other fetch
# writes it, so none run alongside can move it between the fetch and the resolve
BASE_REF = "refs/brain-sync/base"
# origin's main alone into BASE_REF, no tags, no submodules, FETCH_HEAD left as it was
FETCH = ("fetch", "--no-tags", "--no-recurse-submodules", "--no-write-fetch-head", REMOTE, f"+{MAIN_REF}:{BASE_REF}")
# one ref, a machine-readable verdict per ref, tags and submodules off; never --force
PUSH = ("push", "--porcelain", "--no-follow-tags", "--no-recurse-submodules", REMOTE)
# the seconds a fetch or push may run
NETWORK_TIMEOUT = 300
# the home repo's command, on PATH, that pulls origin into the install copy and switches it
APPLY_COMMAND = "sy"


class Stop(StrEnum):
    """every way one repo's sync stops for him to act on; `b-sync -h` lists them from here."""

    REMOTE = "origin fetches from more than one url, or pushes somewhere other than the one url it fetches from"
    FETCH = f"origin's {MAIN_REF} could not be fetched into {BASE_REF}, or {BASE_REF} names no commit"
    LEARNER = (f"a learner worktree is locked, its learner still running: run {TOOL} again after it finishes; "
               "or, if it died, `git -C <brain> worktree unlock <path>`; or it holds uncommitted changes: "
               "commit them on its learn/* branch, or discard them by hand")
    STAGED = "the scan of the work tree before its commit did not pass, or could not run"
    MERGING = "a merge is in progress on a branch other than brain-sync"
    CONFLICT = "a merge stopped on conflicting files; it is left in progress on brain-sync to resolve"
    STALE = "a brain-sync branch exists but is not checked out: switch to it to resume, or delete it"
    GIT = "a local git read or write failed or ran past its timeout"
    OUTGOING = "the scan of what the push sends did not pass, or could not run"
    MOVED = f"origin's main moved under each of {PUSH_ATTEMPTS} pushes"
    PUSH = ("the push failed for a reason other than origin moving, or ran past its timeout "
            f"(origin may then hold the tip; running {TOOL} again resumes)")
    FOLLOW = "origin holds the tip, but local main would not follow it or brain-sync would not delete"
    APPLY = (f"every repo is pushed, but {APPLY_COMMAND} is not on PATH or failed, so the install copy lacks "
             f"the push: deal with the cause and run {APPLY_COMMAND}")

    @property
    def exit(self) -> Exit:
        """the code b-sync exits with on this stop.

        # Returns

        `Exit.CONFLICT` for a conflict, `Exit.BLOCKED` for every other stop
        """
        return Exit.CONFLICT if self is Stop.CONFLICT else Exit.BLOCKED

    @classmethod
    def legend(cls) -> str:
        r"""every stop, one line each, as `b-sync -h` prints them.

        # Returns

        `  <name> (exit <code>): <what happened>` per stop, in declaration order

        # Example

            >>> print("\n".join(Stop.legend().splitlines()[4:6]))
              merging (exit 5): a merge is in progress on a branch other than brain-sync
              conflict (exit 3): a merge stopped on conflicting files; it is left in progress on brain-sync to resolve
        """
        return "\n".join(f"  {stop.name.lower()} (exit {stop.exit.value}): {stop}" for stop in cls)


class SyncError(Exception):
    """one repo stopped; `main` prints it and exits with its stop's code."""

    def __init__(self, repo: Path, stop: Stop, detail: str) -> None:
        """the repo, the stop, and what this occurrence of it found.

        # Arguments

        * `repo` - the work tree that stopped
        * `stop` - which way it stopped
        * `detail` - what git or the scan said, worded for him to act on
        """
        super().__init__(f"{repo}: {stop}: {detail}")
        self.stop: Stop = stop

    @classmethod
    def of(cls, repo: Path, stop: Stop, run: GitRun) -> "SyncError":
        """the stop a git run that did not end OK leaves.

        # Arguments

        * `repo` - the work tree that stopped
        * `stop` - which way it stopped
        * `run` - the git run, whose command, ending and reason are the detail

        # Returns

        the error, its detail the run and, when git exited, each line of its
        reason (`GitRun.detail`) indented below it
        """
        said = "".join(f"\n  {line}" for line in run.detail.splitlines()) if run.code is not None else ""
        return cls(repo, stop, f"{run}{said}")


@dataclass(frozen=True)
class Repo:
    """one git work tree that syncs to origin main."""

    path: Path

    def run(self, *argv: str, timeout: float = LONG_GIT_TIMEOUT) -> GitRun:
        """run a git command as arpadav, echoing it as a shell would re-run it (P59).

        # Arguments

        * `argv` - the git subcommand and its arguments
        * `timeout` - seconds before the command is killed

        # Returns

        the run and how it ended
        """
        print(f"+ {shlex.join(('git', '-C', str(self.path), *IDENTITY, *argv))}", file=sys.stderr)
        return GitRun.of(self.path, *IDENTITY, *argv, timeout=timeout)

    def write(self, stop: Stop, *argv: str, timeout: float = LONG_GIT_TIMEOUT) -> None:
        """run a git command that must end OK.

        # Arguments

        * `stop` - the stop any other ending is
        * `argv` - the git subcommand and its arguments
        * `timeout` - seconds before the command is killed

        # Raises

        SyncError with `stop` unless the run ended OK
        """
        if not (done := self.run(*argv, timeout=timeout)).ok:
            raise SyncError.of(self.path, stop, done)

    def read(self, *argv: str, stop: Stop = Stop.GIT) -> str:
        """stdout of a read-only git command over the history as stored, never echoed.

        LONG_GIT_TIMEOUT bounds it: a status reads every submodule

        # Arguments

        * `argv` - the git subcommand and its arguments
        * `stop` - the stop a run that does not end OK is

        # Returns

        stdout with surrounding whitespace stripped

        # Raises

        SyncError with `stop` unless the run ended OK
        """
        if not (done := GitRun.of(self.path, NO_REPLACE, *argv, timeout=LONG_GIT_TIMEOUT)).ok:
            raise SyncError.of(self.path, stop, done)
        return done.stdout.strip()

    def merging(self) -> bool:
        """whether a merge is in progress.

        # Returns

        True while the repo has a `MERGE_HEAD`, which a stopped merge leaves behind
        """
        return GitRun.of(self.path, "rev-parse", "-q", "--verify", "MERGE_HEAD").ok

    def conflicts(self) -> list[str]:
        """the files still unmerged.

        # Returns

        paths relative to the repo, a non-ascii name as written; empty when the merge left none
        """
        return self.read("-c", "core.quotePath=false", "diff", "--name-only", "--diff-filter=U").splitlines()

    def has_branch(self, name: str) -> bool:
        """whether a local branch exists.

        # Arguments

        * `name` - the branch name, without `refs/heads/`

        # Returns

        True when the branch is present locally
        """
        return GitRun.of(self.path, "rev-parse", "-q", "--verify", f"refs/heads/{name}").ok

    def resume(self) -> None:
        """step 4: commit a merge he resolved on SYNC_BRANCH, with everything step 3 scanned.

        # Raises

        SyncError: MERGING for a merge on any other branch, CONFLICT while a
        file is unmerged, GIT when the add or the commit fails
        """
        if not self.merging():
            return
        if self.read("branch", "--show-current") != SYNC_BRANCH:
            raise SyncError(self.path, Stop.MERGING, "finish or abort it by hand")
        if unmerged := self.conflicts():
            raise SyncError(self.path, Stop.CONFLICT, f"unmerged: {', '.join(unmerged)}")
        self.write(Stop.GIT, "add", "-A", *UNPLANNED)
        self.write(Stop.GIT, "commit", "--no-edit", "-m", MESSAGE)

    def verify_remote(self) -> None:
        """step 1: origin must fetch from one url and push to it, insteadOf and pushInsteadOf expanded.

        # Raises

        SyncError: REMOTE for two fetch urls or a push url that differs, GIT
        when git cannot list them
        """
        fetches = self.read("remote", "get-url", "--all", REMOTE).splitlines()
        pushes = self.read("remote", "get-url", "--push", "--all", REMOTE).splitlines()
        if len(fetches) != 1 or pushes != fetches:
            detail = f"fetches from {', '.join(fetches)}; pushes to {', '.join(pushes)}"
            # one push url is the split a bootstrap clone leaves: fold fetch onto it
            if len(pushes) == 1:
                detail += (
                    f"; to make them one: git -C {self.path} remote set-url origin {pushes[0]}"
                    f" && git -C {self.path} config --unset-all remote.{REMOTE}.pushurl"
                )
            raise SyncError(self.path, Stop.REMOTE, detail)

    def fetch(self) -> str:
        """step 1: fetch origin's main into BASE_REF and resolve it, once, to a commit id.

        # Returns

        BASE: the full id of origin's main, as fetched

        # Raises

        SyncError with FETCH when origin cannot be fetched or BASE_REF names no commit
        """
        self.write(Stop.FETCH, *FETCH, timeout=NETWORK_TIMEOUT)
        return self.read("rev-parse", "--verify", "--end-of-options", f"{BASE_REF}^{{commit}}", stop=Stop.FETCH)

    def even(self, base: str) -> bool:
        """step 2: on main, nothing staged or to stage, at BASE, and no SYNC_BRANCH left over.

        # Arguments

        * `base` - origin's main, as `fetch` resolved it

        # Returns

        True when the repo has nothing to carry to origin main

        # Raises

        SyncError with GIT when git cannot answer

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Repo(Path(tmp).resolve())
            ...     repo.write(Stop.GIT, "init", "-q", "-b", MAIN)
            ...     repo.write(Stop.GIT, "commit", "-q", "--allow-empty", "-m", MESSAGE)
            ...     base = repo.tip()
            ...     clean = repo.even(base)
            ...     (repo.path / PLANS).mkdir()
            ...     _ = (repo.path / PLANS / "x.md").write_text("x")
            ...     planned = repo.even(base)
            ...     _ = (repo.path / "new.nix").write_text("x")
            ...     clean, planned, repo.even(base)
            (True, True, False)
        """
        return (self.read("branch", "--show-current") == MAIN
                and not self.read("diff", "--cached", "--name-only")
                and not self.read("status", "--porcelain", *UNPLANNED)
                and self.tip() == base
                and not self.has_branch(SYNC_BRANCH))

    def cut(self) -> None:
        """step 5: cut SYNC_BRANCH from HEAD, or stay on it, and commit everything on it.

        # Raises

        SyncError: STALE when SYNC_BRANCH exists but is not checked out, GIT
        when a switch, add or commit fails
        """
        if (current := self.read("branch", "--show-current")) != SYNC_BRANCH:
            if self.has_branch(SYNC_BRANCH):
                raise SyncError(self.path, Stop.STALE, f"HEAD is on {current or 'a detached commit'}")
            self.write(Stop.GIT, "switch", "-c", SYNC_BRANCH)
        self.write(Stop.GIT, "add", "-A", *UNPLANNED)
        if self.read("diff", "--cached", "--name-only"):
            self.write(Stop.GIT, "commit", "-m", MESSAGE)

    def merge(self, ref: str) -> None:
        """step 6: merge a commit into HEAD, a merge commit when it is not a fast-forward.

        `--ff` overrides a `merge.ff=only` in his config, which would refuse
        every merge of two diverged histories; a conflict leaves the merge in
        progress

        # Arguments

        * `ref` - BASE's id, MAIN_REF, or a learner's branch by its full ref

        # Raises

        SyncError: CONFLICT when the merge stopped on unmerged files, GIT on
        any other failure or a timeout
        """
        merged = self.run("merge", "--ff", "--no-edit", "-m", MESSAGE, ref)
        if merged.ok:
            return
        if merged.ending is Ending.FAILED and self.merging() and (unmerged := self.conflicts()):
            raise SyncError(self.path, Stop.CONFLICT, f"unmerged: {', '.join(unmerged)}")
        raise SyncError.of(self.path, Stop.GIT, merged)

    def learners(self) -> list["Learner"]:
        """step 3: every linked worktree of this repo checked out on a learner's branch, under LEARNER_PREFIX.

        git lists the main worktree first, and it is never a learner, even
        checked out on a `learn/*` branch: folding it would remove the repo
        being synced

        # Returns

        one Learner per such worktree, in git's order, each in the state git
        reports it in; none for a repo no learner worked in

        # Raises

        SyncError with GIT when git cannot list the worktrees

        # Example

            >>> import shutil, tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Repo(Path(tmp, "brain").resolve())
            ...     repo.path.mkdir()
            ...     repo.write(Stop.GIT, "init", "-q", "-b", "learn/main")
            ...     repo.write(Stop.GIT, "commit", "-q", "--allow-empty", "-m", MESSAGE)
            ...     for name in ("learn/live", "learn/running", "learn/gone", "other"):
            ...         repo.write(Stop.GIT, "worktree", "add", "-q", "-b", name, str(Path(tmp, name)))
            ...     repo.write(Stop.GIT, "worktree", "lock", "--reason", "running", str(Path(tmp, "learn/running")))
            ...     shutil.rmtree(Path(tmp, "learn/gone"))
            ...     [(learner.ref.removeprefix(LEARNER_PREFIX), learner.state.value) for learner in repo.learners()]
            [('gone', 'gone'), ('live', 'live'), ('running', 'running')]
        """
        # `-z`: each field ends in a NUL and each worktree in one more, so a path holding a newline comes back whole
        _main, *linked = self.read("worktree", "list", "--porcelain", "-z").split("\0\0")
        listed = ({key: value for key, _, value in (field.partition(" ") for field in record.split("\0"))}
                  for record in linked)
        return [Learner(Repo(Path(fields["worktree"])), ref, LearnerState.of(fields)) for fields in listed
                if (ref := fields.get("branch", "")).startswith(LEARNER_PREFIX)]

    def admit(self, learners: Iterable["Learner"]) -> None:
        """step 3: every learner may be folded - none still running, none holding uncommitted work.

        # Arguments

        * `learners` - the worktrees `learners` listed

        # Raises

        SyncError with LEARNER naming each learner that may not be folded yet;
        GIT when git cannot read a live worktree's status

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Repo(Path(tmp, "brain").resolve())
            ...     repo.path.mkdir()
            ...     repo.write(Stop.GIT, "init", "-q", "-b", MAIN)
            ...     repo.write(Stop.GIT, "commit", "-q", "--allow-empty", "-m", MESSAGE)
            ...     tree = Path(tmp, "learn")
            ...     repo.write(Stop.GIT, "worktree", "add", "-q", "-b", "learn/s", str(tree))
            ...     repo.write(Stop.GIT, "worktree", "lock", "--reason", "running", str(tree))
            ...     try:
            ...         repo.admit(repo.learners())
            ...     except SyncError as stopped:
            ...         print(stopped.stop.name, str(tree) in str(stopped))
            ...     repo.write(Stop.GIT, "worktree", "unlock", str(tree))
            ...     repo.admit(repo.learners())
            LEARNER True
        """
        if held := [why for learner in learners if (why := learner.hold())]:
            raise SyncError(self.path, Stop.LEARNER, "; ".join(held))

    def fold(self, learner: "Learner") -> None:
        """step 5: merge a learner's branch into HEAD, then remove its worktree and delete the branch.

        its state is read again first and put through `admit` once more: a
        learner of the same session may have locked the worktree again after
        the run's `admit`. a learner whose directory was deleted has nothing
        to remove: the worktree records git keeps for deleted directories are
        pruned instead, which frees its branch to delete

        # Arguments

        * `learner` - a worktree `learners` listed, `admit` let through

        # Raises

        SyncError: LEARNER when the worktree is locked or holds uncommitted
        work again; CONFLICT when the merge stopped on unmerged files, left in
        progress; GIT when the merge, the removal or the deletion fails

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Repo(Path(tmp, "brain").resolve())
            ...     repo.path.mkdir()
            ...     repo.write(Stop.GIT, "init", "-q", "-b", MAIN)
            ...     repo.write(Stop.GIT, "commit", "-q", "--allow-empty", "-m", MESSAGE)
            ...     repo.write(Stop.GIT, "worktree", "add", "-q", "-b", "learn/s", str(Path(tmp, "learn")))
            ...     [learner] = repo.learners()
            ...     _ = (learner.tree.path / "P99.md").write_text("learned")
            ...     idle = learner.idle()
            ...     learner.tree.write(Stop.GIT, "add", "P99.md")
            ...     learner.tree.write(Stop.GIT, "commit", "-q", "-m", MESSAGE)
            ...     repo.write(Stop.GIT, "switch", "-q", "-c", SYNC_BRANCH)
            ...     repo.write(Stop.GIT, "worktree", "lock", "--reason", "running", str(learner.tree.path))
            ...     try:
            ...         repo.fold(learner)
            ...     except SyncError as stopped:
            ...         print(stopped.stop.name)
            ...     repo.write(Stop.GIT, "worktree", "unlock", str(learner.tree.path))
            ...     repo.fold(learner)
            ...     idle, (repo.path / "P99.md").read_text(), repo.learners(), repo.has_branch("learn/s")
            LEARNER
            (False, 'learned', [], False)

        a learner whose directory was deleted after its commit:

            >>> import shutil, tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Repo(Path(tmp, "brain").resolve())
            ...     repo.path.mkdir()
            ...     repo.write(Stop.GIT, "init", "-q", "-b", MAIN)
            ...     repo.write(Stop.GIT, "commit", "-q", "--allow-empty", "-m", MESSAGE)
            ...     tree = Repo(Path(tmp, "learn"))
            ...     repo.write(Stop.GIT, "worktree", "add", "-q", "-b", "learn/s", str(tree.path))
            ...     _ = (tree.path / "P99.md").write_text("learned")
            ...     tree.write(Stop.GIT, "add", "P99.md")
            ...     tree.write(Stop.GIT, "commit", "-q", "-m", MESSAGE)
            ...     shutil.rmtree(tree.path)
            ...     repo.write(Stop.GIT, "switch", "-q", "-c", SYNC_BRANCH)
            ...     [learner] = repo.learners()
            ...     repo.fold(learner)
            ...     (repo.path / "P99.md").read_text(), repo.learners(), repo.has_branch("learn/s")
            ('learned', [], False)
        """
        # --------------------------------------------------
        # its state re-read: a learner may have locked it again since `admit`;
        # one git no longer lists keeps the state it was listed in
        # --------------------------------------------------
        learner = next((now for now in self.learners() if now.ref == learner.ref), learner)
        self.admit([learner])
        self.merge(learner.ref)
        if learner.state is LearnerState.GONE:
            self.write(Stop.GIT, "worktree", "prune")
        else:
            self.write(Stop.GIT, "worktree", "remove", str(learner.tree.path))
        self.write(Stop.GIT, "branch", "-d", learner.ref.removeprefix("refs/heads/"))

    def tip(self) -> str:
        """HEAD, resolved once to a commit id: step 2 compares it to BASE, step 6 takes it as TIP.

        # Returns

        the full id of HEAD's commit; as TIP, the commit the scan reads and the push sends
        """
        return self.read("rev-parse", "--verify", "--end-of-options", "HEAD^{commit}")

    def follow(self, tip: str) -> None:
        """step 9: main follows what origin accepted, made at it when there is none, and SYNC_BRANCH goes.

        main is moved to TIP from TIP, never checked out at its old commit:
        that checkout would write back the files old main tracks and TIP does
        not, over an untracked or ignored copy on disk - a plan file TIP
        stopped tracking among them - and moving on to TIP would then delete
        them

        # Arguments

        * `tip` - TIP, which origin's main now holds and HEAD is at

        # Raises

        SyncError with FOLLOW when main is not an ancestor of TIP, or main
        will not move or the branch will not delete

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     repo = Repo(Path(tmp).resolve())
            ...     repo.write(Stop.GIT, "init", "-q", "-b", MAIN)
            ...     (repo.path / PLANS).mkdir()
            ...     _ = (repo.path / PLANS / "x.md").write_text("committed")
            ...     repo.write(Stop.GIT, "add", "-A")
            ...     repo.write(Stop.GIT, "commit", "-q", "-m", MESSAGE)
            ...     repo.write(Stop.GIT, "switch", "-q", "-c", SYNC_BRANCH)
            ...     repo.write(Stop.GIT, "rm", "-q", "--cached", f"{PLANS}/x.md")
            ...     repo.write(Stop.GIT, "commit", "-q", "-m", MESSAGE)
            ...     _ = (repo.path / PLANS / "x.md").write_text("his edit")
            ...     repo.follow(repo.tip())
            ...     repo.read("branch", "--show-current"), (repo.path / PLANS / "x.md").read_text()
            ('main', 'his edit')
        """
        if self.has_branch(MAIN):
            self.write(Stop.FOLLOW, "merge-base", "--is-ancestor", MAIN_REF, tip)
        self.write(Stop.FOLLOW, "switch", "-C", MAIN, tip)
        self.write(Stop.FOLLOW, "branch", "-d", SYNC_BRANCH)

    def sync(self, guard: "Guard") -> None:
        """carry this repo's work to origin main: the module doc's steps 1 to 9.

        # Arguments

        * `guard` - the private scan this run puts every repo through

        # Raises

        SyncError naming the stop, at the first step that cannot go on
        """
        # --------------------------------------------------
        # origin's main, from the one url the push goes to; nothing to carry ends here
        # --------------------------------------------------
        self.verify_remote()
        base = self.fetch()
        learners = self.learners()
        if not learners and self.even(base):
            return
        # --------------------------------------------------
        # no learner still running, none with work left behind uncommitted
        # --------------------------------------------------
        self.admit(learners)
        # --------------------------------------------------
        # nothing private goes into a commit, then a merge he resolved
        # --------------------------------------------------
        guard.scan(self.path, Stop.STAGED)
        self.resume()
        # --------------------------------------------------
        # the work, committed on its own branch, then every learner's merged into it
        # --------------------------------------------------
        self.cut()
        for learner in learners:
            self.fold(learner)
        for attempt in range(1, PUSH_ATTEMPTS + 1):
            # --------------------------------------------------
            # BASE, then local main, into the branch; its tip, once
            # --------------------------------------------------
            self.merge(base)
            if self.has_branch(MAIN):
                self.merge(MAIN_REF)
            tip = self.tip()
            # --------------------------------------------------
            # nothing the push sends carries a private value
            # --------------------------------------------------
            guard.scan(self.path, Stop.OUTGOING, base, tip)
            # --------------------------------------------------
            # TIP to origin's main; only a refused fast-forward goes round again
            # --------------------------------------------------
            pushed = self.run(*PUSH, f"{tip}:{MAIN_REF}", timeout=NETWORK_TIMEOUT)
            match pushed.ending:
                case Ending.OK:
                    self.follow(tip)
                    return
                case Ending.FAILED | Ending.TIMED_OUT:
                    raise SyncError.of(self.path, Stop.PUSH, pushed)
                case Ending.REJECTED if attempt < PUSH_ATTEMPTS:
                    print(f"{TOOL}: {self.path}: origin's main moved since the fetch; "
                          f"round {attempt + 1} of {PUSH_ATTEMPTS}", file=sys.stderr)
                    base = self.fetch()
                case Ending.REJECTED:
                    raise SyncError.of(self.path, Stop.MOVED, pushed)


class LearnerState(StrEnum):
    """where a learner's worktree stands, as `git worktree list` reports it."""

    # its directory is there and unlocked: folded once nothing in it is uncommitted
    LIVE = "live"
    # locked: brain-learner holds the lock from `worktree add` to its commit, so it is never folded
    RUNNING = "running"
    # prunable: its directory was deleted; its branch is folded and the stale record pruned
    GONE = "gone"

    @classmethod
    def of(cls, fields: dict[str, str]) -> "LearnerState":
        """the state one record of `git worktree list --porcelain` reports.

        # Arguments

        * `fields` - the record's fields, each by its label; `locked` and
          `prunable` are present, reason or none, only when they hold

        # Returns

        RUNNING when locked, git never reporting a locked worktree prunable;
        else GONE when prunable; else LIVE

        # Example

            >>> [LearnerState.of(fields).value for fields in ({"locked": ""}, {"prunable": "gone"}, {})]
            ['running', 'gone', 'live']
        """
        if "locked" in fields:
            return cls.RUNNING
        return cls.GONE if "prunable" in fields else cls.LIVE


@dataclass(frozen=True)
class Learner:
    """one learner's worktree of a repo, checked out on its own branch under LEARNER_PREFIX (brain-learner)."""

    tree: Repo
    # the branch, by its full ref, which no tag can shadow
    ref: str
    # where the worktree stands, which decides whether and how it is folded
    state: LearnerState

    def idle(self) -> bool:
        """whether the worktree holds nothing uncommitted, untracked files included; folding never discards.

        # Returns

        True when `git status` there lists nothing

        # Raises

        SyncError with GIT when git cannot read the worktree's status
        """
        return not self.tree.read("status", "--porcelain")

    def hold(self) -> str:
        """why this learner may not be folded yet.

        # Returns

        the reason, naming the worktree, for one still running or holding
        uncommitted work; "" for one that may be folded

        # Raises

        SyncError with GIT when git cannot read a live worktree's status
        """
        match self.state:
            case LearnerState.RUNNING:
                return f"{self.tree.path} is locked, its learner still running"
            case LearnerState.LIVE if not self.idle():
                return f"uncommitted in {self.tree.path}"
            case _:
                return ""


@dataclass(frozen=True)
class Guard:
    """the private scan one run puts every repo through, its values probed once, at the first scan (P61).

    the scan runs in this process, so the probes of this machine run once per
    run, not once per repo and scan, and every scan of the run looks for the
    same values. a run with nothing to carry probes nothing
    """

    @cached_property
    def values(self) -> PrivateScan:
        """the values every scan of this run looks for, gathered at the first call.

        # Returns

        the scan over every source's values

        # Raises

        NoVerdict when private.toml is malformed or no source gives a value
        """
        return PrivateScan.gather(XdgLayout.private_toml())

    def scan(self, repo: Path, stop: Stop, since: str = "", tip: str = "") -> None:
        """scan one repo alone, as b-private over it would, echoing that command (P59).

        # Arguments

        * `repo` - the work tree to scan
        * `stop` - the stop anything but a pass is
        * `since` - BASE, to scan the commits a push of `tip` sends; "" scans
          the work tree
        * `tip` - TIP, the commit the push sends

        # Raises

        SyncError with `stop` on anything but a pass: a hit, an unscanned file,
        and a scan that gave no verdict
        """
        flags = (Flag.SINCE, since, Flag.TIP, tip) if since else ()
        print(f"+ {shlex.join((Layout.command(Layout.PRIVATE), *flags, str(repo)))}  # in this process",
              file=sys.stderr, flush=True)
        try:
            scope = ScanScope.of(RepoTree.containing(repo))
            source = scope.source(since, tip)
            scope.announce(source)
            verdict = self.values.run(source)
        except NoVerdict as blind:
            raise SyncError(repo, stop, f"the private scan gave no verdict: {blind}") from blind
        if verdict is not Exit.OK:
            raise SyncError(repo, stop, "the private scan hit; each hit is printed above")


@dataclass(frozen=True)
class Sync:
    """the brain's repos in push order - submodules, the store, its superproject - and the submodules left out."""

    repos: tuple[Repo, ...]
    # the store's submodules this clone never checked out: never synced, each named in a warning
    unopened: tuple[Path, ...]

    @classmethod
    def discover(cls) -> "Sync":
        """the repos around the edit copy's brain, whichever copy this script runs from.

        # Returns

        `Sync.of` the brain `XdgLayout.edit_brain()` names

        # Raises

        EditCopyMissing, a NoVerdict, when this machine has no edit copy;
        NoVerdict when repos.toml cannot be read or is not of its shape;
        SyncError with GIT when git cannot list its repos

        # Example

            >>> import os, tempfile
            >>> from unittest import mock
            >>> from brainlib import EditCopyMissing, Env
            >>> with (tempfile.TemporaryDirectory() as tmp,
            ...       mock.patch.dict(os.environ, {"HOME": tmp, Env.XDG_CONFIG_HOME: ""})):
            ...     try:
            ...         _ = Sync.discover()
            ...     except EditCopyMissing as missing:
            ...         print(missing)
            ...     brain = Repo(Path(tmp, "repos", "personal", "home", "brain").resolve())
            ...     (brain.path / "bin").mkdir(parents=True)
            ...     brain.write(Stop.GIT, "init", "-q")
            ...     Sync.discover().repos == (brain,)
            no edit copy - run /home-setup
            True
        """
        return cls.of(XdgLayout.edit_brain())

    @classmethod
    def of(cls, brain: Path) -> "Sync":
        """the repos around one brain store.

        the submodules are read off the store's index, so a path holding a
        space comes back whole; one never checked out is set aside, since git
        run in its empty directory answers for the store

        # Arguments

        * `brain` - the brain store's work tree

        # Returns

        the store's checked-out submodules, then the store, then the
        superproject that holds it, if any; and the submodules not checked out

        # Raises

        SyncError with GIT when git cannot list them

        # Example

            >>> import tempfile
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     store = Repo(Path(tmp).resolve())
            ...     store.write(Stop.GIT, "init", "-q")
            ...     for name in ("my sub", "logs"):
            ...         (store.path / name).mkdir()
            ...         store.write(Stop.GIT, "update-index", "--add", "--cacheinfo", f"160000,{'1' * 40},{name}")
            ...     Repo(store.path / "my sub").write(Stop.GIT, "init", "-q")
            ...     sync = Sync.of(store.path)
            ...     synced = [repo.path.relative_to(store.path).as_posix() for repo in sync.repos]
            ...     synced, [path.name for path in sync.unopened]
            (['my sub', '.'], ['logs'])
        """
        store = Repo(brain)
        # not RepoTree.around: push order wants the store's own submodules and its DIRECT superproject only
        try:
            linked = RepoTree.gitlinks(brain)
        except RepoError as broken:
            raise SyncError(brain, Stop.GIT, str(broken)) from broken
        inner = tuple(Repo(path) for path in linked if RepoTree.checked_out(path))
        outer = store.read("rev-parse", "--show-superproject-working-tree")
        return cls((*inner, store, *((Repo(Path(outer)),) if outer else ())),
                   tuple(path for path in linked if not RepoTree.checked_out(path)))

    def check(self) -> Exit:
        """print each repo's state; change nothing.

        # Returns

        `Exit.OK`

        # Raises

        SyncError with GIT when git cannot read a repo's status
        """
        for repo in self.repos:
            learned = "".join(f"\nlearner {learner.ref} at {learner.tree.path}: {learner.state}"
                              for learner in repo.learners())
            print(f"{repo.path}\n{repo.read('status', '-sb')}{learned}\n")
        return Exit.OK

    def push(self) -> Exit:
        """sync every repo innermost first, then apply them to the install copy; the first stop ends the run.

        # Returns

        `Exit.OK` when every repo synced and `apply` ran

        # Raises

        SyncError at the first repo that stops, or with APPLY
        """
        guard = Guard()
        for repo in self.repos:
            repo.sync(guard)
            print(f"{TOOL}: {repo.path} synced to {REMOTE}/{MAIN}", flush=True)
        return self.apply()

    @staticmethod
    def apply() -> Exit:
        """run APPLY_COMMAND, which pulls origin into the install copy and switches it, echoing it first (P59).

        # Returns

        `Exit.OK` when it exited 0

        # Raises

        SyncError with APPLY, against the install copy, when it is not on
        PATH, cannot start or exits non-zero
        """
        install = XdgLayout.install_home()
        if (found := shutil.which(APPLY_COMMAND)) is None:
            raise SyncError(install, Stop.APPLY, f"{APPLY_COMMAND} is not on PATH")
        print(f"Running: {APPLY_COMMAND}", flush=True)
        # the home repo's own command, found on PATH, no arguments, no shell (S603)
        try:
            code = subprocess.run([found], check=False).returncode  # noqa: S603
        except OSError as broken:
            raise SyncError(install, Stop.APPLY, f"{APPLY_COMMAND} cannot start: {broken}") from broken
        if code:
            raise SyncError(install, Stop.APPLY, f"{APPLY_COMMAND} exited {code}")
        return Exit.OK

    def warnings(self) -> list[str]:
        """what to tell him about the submodules left out.

        # Returns

        one warning per submodule this clone never checked out
        """
        return [f"{TOOL}: warning: {path} is a submodule this clone never checked out; it is not synced"
                for path in self.unopened]

    @staticmethod
    def undeclared() -> list[str]:
        """what to tell him when no declared value is checked this run.

        # Returns

        one warning when `XdgLayout.private_toml()` is not a file, else none
        """
        declared = XdgLayout.private_toml()
        if declared.is_file():
            return []
        return [f"{TOOL}: warning: no {declared}; no scan this run checks his declared values"]

    @staticmethod
    def warn(lines: Iterable[str]) -> None:
        """print warnings on stdout, each flushed so it prints before any later stderr line.

        # Arguments

        * `lines` - the warnings, each a whole line
        """
        for line in lines:
            print(line, flush=True)


def main(args: Args) -> Exit:
    """print each repo's state under --check, else sync; the warnings open and close the run.

    # Arguments

    * `args` - the parsed command line; `--check` prints state and changes nothing

    # Returns

    `Exit.OK` when every repo reached origin main and the install copy took
    it (or `--check` ran), else the stop's exit: `Exit.CONFLICT` or `Exit.BLOCKED`

    # Raises

    NoVerdict - EditCopyMissing among them - when this machine has no edit
    copy or repos.toml cannot be read, which `Tool.run` turns into exit 1
    """
    PrivateScan.name_safe_stdout()
    warned = Sync.undeclared()
    try:
        Sync.warn(warned)
        sync = Sync.discover()
        Sync.warn(unopened := sync.warnings())
        warned += unopened
        return sync.check() if args.has(Flag.CHECK) else sync.push()
    except SyncError as stopped:
        print(f"{TOOL}: {stopped}", file=sys.stderr, flush=True)
        return stopped.stop.exit
    finally:
        Sync.warn(warned)


if __name__ == "__main__":
    # -h: the steps, then every stop, then the signature
    steps, signed, author = (__doc__ or "").rpartition("Author:")
    Tool.of(TOOL, f"{steps}stops (each message names one):\n{Stop.legend()}\n\n{signed}{author}").run(main)
