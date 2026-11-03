#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""b-verify: the checks a repo declares for the files that changed, and the private scan every run gets.

a repo states part of its own bar in a `verify.toml` at its root: each
`[[check]]` names the paths it covers and the command that proves them. the
install matrix of a home-manager repo is the case it exists for - a change to a
nix file is only sound once every install combination still builds, and no
generic build-and-test step knows that.

the change is everything uncommitted, untracked included, across the outermost
repo and every submodule under it, so an edit inside a submodule still fires a
check its superproject declares. paths in a `verify.toml` are relative to the
repo that holds it and matched with fnmatch, where `*` crosses directories.

the private scan (b-private) runs on every run; its -h says what it
covers. every check, that one included, is a process judged by its exit code:
OK passes, FINDINGS is a finding, and anything else - a crash, a command that
cannot start, a code outside that vocabulary - is FAILED. a `verify.toml` or a
row this cannot use is a check that fires on every run and FAILS without
running. whatever one check does, the next one still runs, and the tally ends
FAILED if any check failed, else FINDINGS if any had findings, else OK.

    b-verify     # print the checks the change fires
    b-verify -r  # run them in turn, then the tally

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
from brainlib import Args, Exit, Flag, Json, Layout, RepoTree, Tool, read_text

# --------------------------------------------------
# external
# --------------------------------------------------
import fnmatch
import shlex
import shutil
import subprocess
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages
TOOL = Layout.command(Path(__file__))
# the file a repo declares its checks in, at its root
DECLARATION = "verify.toml"
# how many covered paths a listing names before eliding the rest
SHOWN = 4
# the brain this script runs from, which holds the private scan
LAYOUT = Layout.discover()


@dataclass(frozen=True)
class Check:
    """one check: what it is called, what it covers, how it runs."""

    repo: Path
    name: str
    # () for the built-in private scan and a faulty row: each fires on every run
    when: tuple[str, ...]
    argv: tuple[str, ...]
    # why a declared row cannot run; empty for a sound check
    fault: str = ""

    @classmethod
    def private(cls, top: Path) -> "Check":
        """the built-in check: b-private's scan of the tree around `top` (P61).

        # Arguments

        * `top` - the directory the scan runs from, standing in for the check's repo

        # Returns

        a check that fires on every run
        """
        return cls(top, "private values", (), LAYOUT.private_command)

    @classmethod
    def declared(cls, repos: Iterable[Path]) -> list["Check"]:
        r"""every check the repos declare.

        # Arguments
        * `repos` - the repos whose `verify.toml` to read

        # Returns
        one Check per `[[check]]` row, its `repo` the repo that declared it and
        its `run` split once, without a shell; a file it cannot read is one
        faulty check, and so is each row it cannot use

        # Example

            >>> import tempfile
            >>> rows = ('[[check]]', 'name = "m"', 'when = ["*.nix"]', 'run = "debug/m.sh -q"',
            ...         '[[check]]', 'name = "s"', 'when = "*.nix"', 'run = "x"', '[[check]]', 'run = ""')
            >>> with tempfile.TemporaryDirectory() as tmp:
            ...     _ = (Path(tmp) / DECLARATION).write_text("\n".join(rows))
            ...     for check in Check.declared([Path(tmp)]):
            ...         print(check.name, check.argv, check.fault or "sound")
            m ('debug/m.sh', '-q') sound
            s () `when` is not a list of strings
            verify.toml () a row without a string `name`
        """
        out: list[Check] = []
        for repo in repos:
            if not (path := repo / DECLARATION).exists():
                continue
            try:
                rows = tomllib.loads(read_text(path)).get("check", [])
            # TOMLDecodeError and UnicodeDecodeError are both ValueErrors
            except (OSError, ValueError) as broken:
                out.append(cls(repo, DECLARATION, (), (), f"unreadable: {broken}"))
                continue
            out += [cls.row(repo, row) for row in (Json.members(rows) if Json.is_array(rows) else [rows])]
        return out

    @classmethod
    def row(cls, repo: Path, row: object) -> "Check":
        """one `[[check]]` row as a Check; a faulty one when a field is missing or mistyped.

        # Arguments

        * `repo` - the repo whose declaration file held the row
        * `row` - the parsed row, of any shape; `name`, `run` and `when` are read from it

        # Returns

        the check, or a faulty one carrying the reason, which `main` fires and fails
        on rather than dropping a row that was meant to guard something
        """
        fields = Json.fields(row)
        name, when = Json.text(fields.get("name")), fields.get("when")
        patterns = tuple(map(Json.text, Json.members(when)))
        try:
            argv = tuple(shlex.split(Json.text(fields.get("run"))))
        except ValueError:
            argv = ()
        if not name:
            return cls(repo, DECLARATION, (), (), "a row without a string `name`")
        if not argv:
            return cls(repo, name, (), (), "`run` is empty, not a string, or unbalanced in its quotes")
        if not Json.is_array(when) or not all(patterns):
            return cls(repo, name, (), (), "`when` is not a list of strings")
        return cls(repo, name, patterns, argv)

    def covers(self, changed: list[Path]) -> list[str]:
        """the changed paths inside this check's repo that it covers.

        # Arguments
        * `changed` - absolute paths of every changed file

        # Returns
        the covered paths, relative to the repo, in input order

        # Example

            >>> c = Check(Path("/r"), "m", ("*.nix", "brain/module.nix"), ("x",))
            >>> c.covers([Path("/r/aedit/module.nix"), Path("/r/README.md"), Path("/elsewhere/a.nix")])
            ['aedit/module.nix']
        """
        inside = [str(p.relative_to(self.repo)) for p in changed if p.is_relative_to(self.repo)]
        return [p for p in inside if any(fnmatch.fnmatchcase(p, pattern) for pattern in self.when)]

    def execute(self) -> Exit:
        """run the check's command with the repo root as cwd, echoing it first (P59).

        # Returns
        OK or FINDINGS as the command exited; FAILED for any other exit, a crash
        included, for a command that cannot start, and for a faulty row, which
        prints its fault and runs nothing

        # Example

            >>> finds = Check(Path("."), "finds", (), (sys.executable, "-c", f"raise SystemExit({Exit.FINDINGS})"))
            >>> finds.execute()  # doctest: +ELLIPSIS
            + (cd . && ... -c 'raise SystemExit(4)')
            <Exit.FINDINGS: 4>
            >>> Check(Path("."), "gone", (), ("no-such-command-x",)).execute()  # doctest: +ELLIPSIS
            + (cd . && no-such-command-x)
            b-verify: gone cannot start: ...
            <Exit.FAILED: 1>
            >>> Check(Path("."), "s", (), (), "`when` is not a list of strings").execute()
            b-verify: s: `when` is not a list of strings
            <Exit.FAILED: 1>
        """
        if self.fault:
            print(f"{TOOL}: {self.name}: {self.fault}")
            return Exit.FAILED
        # --------------------------------------------------
        # show what runs
        # --------------------------------------------------
        print(f"+ (cd {self.repo} && {shlex.join(self.argv)})", flush=True)
        # --------------------------------------------------
        # a command spelled with a slash is a path in the repo, not one on PATH
        # --------------------------------------------------
        head, *rest = self.argv
        command = str(self.repo / head) if "/" in head else head
        found = shutil.which(command) or command
        # --------------------------------------------------
        # the repo's own declaration, split without a shell (S603)
        # --------------------------------------------------
        try:
            code = subprocess.run([found, *rest], cwd=self.repo, check=False).returncode  # noqa: S603
        except OSError as broken:
            print(f"{TOOL}: {self.name} cannot start: {broken}")
            return Exit.FAILED
        return Exit(code) if code in {Exit.OK, Exit.FINDINGS} else Exit.FAILED


def main(args: Args) -> Exit:
    """print the checks the change fires, or run them with `--run`, then the tally.

    # Arguments

    * `args` - the parsed command line; `--run` executes the checks instead of listing them

    # Returns

    `Exit.OK` when listing or when every check passed; under `--run`,
    `Exit.FAILED` if any check could not reach a verdict, else `Exit.FINDINGS`
    if any check reported findings

    # Raises

    RepoError when git cannot list the tree
    """
    # --------------------------------------------------
    # the change, and the declared checks it fires; a faulty one always fires
    # --------------------------------------------------
    tree = RepoTree.around(Path.cwd())
    changed = tree.changed()
    declared = [(check, covered) for check in Check.declared(tree.repos)
                if (covered := check.covers(changed)) or check.fault]
    if not declared:
        print(f"{TOOL}: no declared check covers the {len(changed)} changed path(s)")
    # --------------------------------------------------
    # each check, with what it covers; the private scan first, it is the fast one
    # outside a repo it runs where it was asked, and fails with its refusal
    # --------------------------------------------------
    fired: list[tuple[Check, list[str]]] = [(Check.private(tree.repos[0] if tree.repos else Path.cwd()), []), *declared]
    for check, covered in fired:
        shown = ", ".join(covered[:SHOWN]) + (", ..." if len(covered) > SHOWN else "") if check.when else "every run"
        print(f"{check.name:<20} {check.repo}$ {shlex.join(check.argv)}   ({shown})")
    if not args.has(Flag.RUN):
        return Exit.OK
    # --------------------------------------------------
    # each check in turn, then the tally
    # --------------------------------------------------
    verdicts = [(check.name, check.execute()) for check, _ in fired]
    # FAILED outranks FINDINGS, in the tally line and in the exit code
    named = {code: [name for name, verdict in verdicts if verdict == code] for code in (Exit.FAILED, Exit.FINDINGS)}
    tail = "".join(f"; {code.name}: {', '.join(names)}" for code, names in named.items() if names)
    print(f"{TOOL}: {sum(verdict == Exit.OK for _, verdict in verdicts)}/{len(fired)} passed{tail}")
    return next((code for code, names in named.items() if names), Exit.OK)


if __name__ == "__main__":
    Tool.of(TOOL, __doc__).run(main)
