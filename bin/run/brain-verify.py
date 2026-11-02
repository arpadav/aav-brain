#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-verify: the checks a repo declares for the files that changed.

a repo states part of its own bar in a `verify.toml` at its root: each
`[[check]]` names the paths it covers and the command that proves them. the
install matrix of a home-manager repo is the case it exists for - a change to a
nix file is only sound once every install combination still builds, and no
generic build-and-test step knows that.

the change is everything uncommitted, untracked included, across the outermost
repo and every submodule under it, so an edit inside a submodule still fires a
check its superproject declares. paths in a `verify.toml` are relative to the
repo that holds it and matched with fnmatch, where `*` crosses directories.

    python3 brain-verify.py         # print the checks the change fires
    python3 brain-verify.py --run   # run them in turn; non-zero if any fails

    # verify.toml
    [[check]]
    name = "install matrix"
    when = ["*.nix", "install.sh"]
    run = "debug/matrix.sh"

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Exit, Flag, git

# --------------------------------------------------
# external
# --------------------------------------------------
import fnmatch
import shlex
import shutil
import subprocess
import tomllib
from dataclasses import dataclass

# --------------------------------------------------
# constants
# --------------------------------------------------
TOOL = Path(__file__).stem
# the file a repo declares its checks in, at its root
DECLARATION = "verify.toml"
# how many covered paths a listing names before eliding the rest
SHOWN = 4


@dataclass(frozen=True)
class Check:
    """one declared check: what it is called, what it covers, how it runs."""

    repo: Path
    name: str
    when: tuple[str, ...]
    run: str

    def covers(self, changed: list[Path]) -> list[str]:
        """the changed paths inside this check's repo that it covers.

        # Arguments
        * `changed` - absolute paths of every changed file

        # Returns
        the covered paths, relative to the repo, in input order

        # Example

            >>> c = Check(Path("/r"), "m", ("*.nix", "brain/module.nix"), "x")
            >>> c.covers([Path("/r/aedit/module.nix"), Path("/r/README.md"), Path("/elsewhere/a.nix")])
            ['aedit/module.nix']
        """
        inside = [str(p.relative_to(self.repo)) for p in changed if p.is_relative_to(self.repo)]
        return [p for p in inside if any(fnmatch.fnmatchcase(p, pattern) for pattern in self.when)]

    def execute(self) -> bool:
        """run the check's command with the repo root as cwd, echoing it first (P59).

        # Returns
        true when the command exited 0
        """
        # --------------------------------------------------
        # show what runs
        # --------------------------------------------------
        print(f"+ (cd {self.repo} && {self.run})", flush=True)
        # --------------------------------------------------
        # a command spelled with a slash is a path in the repo, not one on PATH
        # --------------------------------------------------
        argv = shlex.split(self.run)
        head = str(self.repo / argv[0]) if "/" in argv[0] else argv[0]
        found = shutil.which(head) or head
        # --------------------------------------------------
        # the repo's own declaration, split without a shell (S603)
        # --------------------------------------------------
        return subprocess.run([found, *argv[1:]], cwd=self.repo, check=False).returncode == 0  # noqa: S603


@dataclass(frozen=True)
class Tree:
    """the outermost repo around the cwd and every submodule under it."""

    repos: tuple[Path, ...]

    @classmethod
    def discover(cls, start: Path) -> "Tree":
        """climb to the outermost superproject, then list its submodules.

        # Arguments
        * `start` - any directory inside the tree

        # Returns
        the Tree; empty when `start` is not in a repo
        """
        # --------------------------------------------------
        # the repo around start
        # --------------------------------------------------
        here = git(start, "rev-parse", "--show-toplevel")
        if here is None:
            return cls(())
        top = Path(here.strip())
        # --------------------------------------------------
        # climb to the outermost superproject, then list its submodules
        # --------------------------------------------------
        while outer := (git(top, "rev-parse", "--show-superproject-working-tree") or "").strip():
            top = Path(outer)
        status = git(top, "submodule", "status", "--recursive") or ""
        inner = [top / line.split()[1] for line in status.splitlines() if line.strip()]
        return cls((top, *inner))

    def changed(self) -> list[Path]:
        """every uncommitted path in every repo of the tree.

        # Returns
        absolute paths, untracked files included, submodule pointers dropped
        """
        # --------------------------------------------------
        # uncommitted and untracked paths, per repo
        # --------------------------------------------------
        out: list[Path] = []
        for repo in self.repos:
            listed = (git(repo, "diff", "--name-only", "HEAD") or "") + (
                git(repo, "ls-files", "--others", "--exclude-standard") or "")
            out += [repo / name for name in listed.splitlines() if name.strip()]
        # --------------------------------------------------
        # a submodule's own pointer shows as a changed path in its parent; it is the
        # submodule's files that say what changed, so the bare directory is dropped
        # --------------------------------------------------
        return [p for p in out if p not in self.repos]

    def checks(self) -> list[Check]:
        """every check declared by any repo in the tree.

        # Returns
        one Check per `[[check]]` row, its `repo` the repo that declared it
        """
        declared = [(repo, repo / DECLARATION) for repo in self.repos if (repo / DECLARATION).exists()]
        return [Check(repo, row["name"], tuple(row["when"]), row["run"])
                for repo, path in declared
                for row in tomllib.loads(path.read_text(encoding="utf-8")).get("check", [])]


def main() -> None:
    """print the checks the change fires, or run them with `--run`.

    exits Exit.OK, or Exit.FAILED when a check run under `--run` fails
    """
    # --------------------------------------------------
    # this tool takes one flag
    # --------------------------------------------------
    args = Args.from_argv()
    if unknown := args.unknown(Flag.RUN):
        sys.exit(f"{TOOL}: unknown flag {unknown[0]}")
    # --------------------------------------------------
    # the change, and the checks it fires
    # --------------------------------------------------
    tree = Tree.discover(Path.cwd())
    changed = tree.changed()
    fired = [(check, covered) for check in tree.checks() if (covered := check.covers(changed))]
    if not fired:
        print(f"{TOOL}: no declared check covers the {len(changed)} changed path(s)")
        sys.exit(Exit.OK)
    # --------------------------------------------------
    # each fired check, with the paths that fired it
    # --------------------------------------------------
    for check, covered in fired:
        print(f"{check.name:<20} {check.repo}$ {check.run}   ({', '.join(covered[:SHOWN])}"
              f"{', ...' if len(covered) > SHOWN else ''})")
    if not args.has(Flag.RUN):
        sys.exit(Exit.OK)
    # --------------------------------------------------
    # run each in turn, then the tally
    # --------------------------------------------------
    failed = [check.name for check, _ in fired if not check.execute()]
    verdict = f"; FAILED: {', '.join(failed)}" if failed else ""
    print(f"{TOOL}: {len(fired) - len(failed)}/{len(fired)} passed{verdict}")
    sys.exit(Exit.FAILED if failed else Exit.OK)


if __name__ == "__main__":
    main()
