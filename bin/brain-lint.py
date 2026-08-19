#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-lint: run every python checker that is installed, against its pinned config.

    python3 brain-lint.py                 check the configured paths
    python3 brain-lint.py bin/foo.py      check specific paths instead
    python3 brain-lint.py --list          show which checkers are reachable, run none

four checkers, four configs, one command. they do not overlap: ruff is a linter
and cannot see types at all - a bare `dict` annotation is invisible to every one
of its 956 rules - while ty, mypy and basedpyright each infer types and each
catches a slightly different slice. so the rule here is not "pick the best one",
it is RUN EVERY ONE THAT IS PRESENT. a checker that is not installed is reported
as skipped, never silently dropped, because a green run that quietly checked two
of four tools is the kind of false confidence this exists to prevent

each checker resolves the same way: use it directly if it is on PATH, else run
it through `uvx` if uv is there, else skip it and say so. every checker's own
output is printed verbatim, and the totals in the summary are the ones the tool
itself reported - this script never counts findings on a tool's behalf

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import PYTHON_VERSION, Args, Flag, Layout

# --------------------------------------------------
# external
# --------------------------------------------------
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
# every path this tool touches, resolved once by the shared discovery
LAYOUT = Layout.discover()
# what gets checked when no path is given on the command line
DEFAULT_PATHS = ("bin",)


@dataclass(frozen=True)
class Checker:
    """one external checker, its pinned config, and how to invoke it."""

    name: str
    config: str
    args: Sequence[str]
    total_re: str
    takes_paths: bool = True
    # a stdlib module is run through this interpreter rather than looked up on PATH
    module: str = ""
    # doctest takes files, not directories, so its paths are expanded first
    expands_dirs: bool = False

    def resolve(self, paths: Sequence[str], root: Path) -> list[str]:
        """the path arguments to hand this checker.

        # Arguments
        * `paths` - the paths the caller asked for
        * `root` - the repo root the checker runs in

        # Returns
        the paths, with directories expanded when the checker cannot walk them
        """
        if not self.takes_paths:
            return []
        if not self.expands_dirs:
            return list(paths)
        out: list[str] = []
        for raw in paths:
            target = root / raw
            out.extend(sorted(str(f.relative_to(root)) for f in target.rglob("*.py"))
                       if target.is_dir() else [raw])
        return out

    def command(self) -> list[str] | None:
        """the argv prefix that runs this checker on this machine.

        # Returns
        the command as a list, or None when neither the tool nor uv is present
        """
        if self.module:
            return [sys.executable, "-m", self.module]
        if shutil.which(self.name):
            return [self.name]
        if shutil.which("uv"):
            return ["uvx", "--python", PYTHON_VERSION, self.name]
        return None

    def total(self, output: str) -> int | None:
        """the finding count the checker reported about itself.

        # Arguments
        * `output` - the checker's combined stdout and stderr

        # Returns
        the tool's own number, or None when it printed no total
        """
        match = re.search(self.total_re, output)
        return int(match.group(1)) if match else None


@dataclass
class Outcome:
    """what one checker did on one run."""

    checker: Checker
    command: list[str] | None = None
    code: int | None = None
    total: int | None = None

    @property
    def skipped(self) -> bool:
        """whether the checker could not be reached at all.

        # Returns
        true when neither the tool nor uv was found
        """
        return self.command is None

    def line(self) -> str:
        """the one-line summary for this checker.

        # Returns
        the summary line: skipped, clean, or the finding count
        """
        if self.command is None:
            return f"  {self.checker.name:14} SKIPPED   not installed, and uv is not available to fetch it"
        how = " ".join(self.command)
        if self.code == 0:
            return f"  {self.checker.name:14} clean     via `{how}`, config {self.checker.config}"
        count = "?" if self.total is None else str(self.total)
        return f"  {self.checker.name:14} {count:>4} FOUND via `{how}`, config {self.checker.config}"


@dataclass
class Suite:
    """every checker, run against one set of paths."""

    checkers: Sequence[Checker]
    root: Path

    def run_one(self, checker: Checker, paths: Sequence[str]) -> Outcome:
        """run a single checker, streaming its own output.

        # Arguments
        * `checker` - the checker to run
        * `paths` - the paths to check

        # Returns
        an Outcome carrying the tool's exit code and its own total
        """
        # --------------------------------------------------
        # resolve the tool, or report it unreachable
        # --------------------------------------------------
        command = checker.command()
        if command is None:
            return Outcome(checker=checker)
        # --------------------------------------------------
        # build the argv and echo it, so a run is reproducible from the log
        # --------------------------------------------------
        argv = command + list(checker.args) + checker.resolve(paths, self.root)
        print(f"\n$ {' '.join(argv)}")
        # stderr is merged rather than suppressed: a checker that dies on a bad
        # config must be visible as a failure, not as a clean run (P36)
        # argv is built from this file's own CHECKERS table plus paths he typed;
        # nothing here is remote input, and shell=False keeps it an exec not a shell (S603)
        result = subprocess.run(argv, cwd=self.root, capture_output=True, text=True, check=False)  # noqa: S603
        # --------------------------------------------------
        # surface the tool's own output, then carry its verdict back
        # --------------------------------------------------
        output = result.stdout + result.stderr
        print(output.rstrip() or "(no output)")
        return Outcome(checker=checker, command=argv, code=result.returncode, total=checker.total(output))

    def run(self, paths: Sequence[str]) -> int:
        """run every checker and summarise.

        # Arguments
        * `paths` - the paths to check

        # Returns
        the exit code: 1 if any reachable checker reported findings
        """
        # --------------------------------------------------
        # run every checker
        # --------------------------------------------------
        outcomes = [self.run_one(checker, paths) for checker in self.checkers]
        # --------------------------------------------------
        # report one line per checker
        # --------------------------------------------------
        print("\nbrain-lint summary")
        for outcome in outcomes:
            print(outcome.line())
        # --------------------------------------------------
        # partition into ran / dirty / skipped, and rule on the suite
        # --------------------------------------------------
        ran = [o for o in outcomes if not o.skipped]
        dirty = [o for o in ran if o.code != 0]
        skipped = [o for o in outcomes if o.skipped]
        if skipped:
            print(f"  {len(skipped)} checker(s) skipped - this run does NOT cover what they would catch")
        if dirty:
            print(f"  {len(dirty)} of {len(ran)} reachable checker(s) reported findings")
            return 1
        print(f"  all {len(ran)} reachable checker(s) clean")
        return 0

# --------------------------------------------------
# constants
# --------------------------------------------------
CHECKERS = (
    Checker(name="ruff", config="ruff.toml", args=("check", "--config", "ruff.toml"),
            total_re=r"Found (\d+) error"),
    Checker(name="ty", config="ty.toml", args=("check", "--config-file", "ty.toml"),
            total_re=r"Found (\d+) diagnostic"),
    Checker(name="mypy", config="mypy.ini", args=("--config-file", "mypy.ini"),
            total_re=r"Found (\d+) error", takes_paths=False),
    Checker(name="basedpyright", config="pyrightconfig.json", args=("--project", "."),
            total_re=r"(\d+) errors?,", takes_paths=False),
    # the repo's only tests: the doctests carried by the pure helpers (aav-style-items §12)
    Checker(name="doctest", config="(inline)", args=(), total_re=r"\*\*\* (\d+) failures",
            module="doctest", expands_dirs=True),
)


def main() -> None:
    """run the suite, or list what is reachable."""
    args = Args.from_argv()
    if unknown := args.unknown(Flag.LIST):
        sys.exit(f"{TOOL}: unknown flag {unknown[0]}")
    if args.has(Flag.LIST):
        for checker in CHECKERS:
            command = checker.command()
            how = " ".join(command) if command else "unreachable"
            print(f"  {checker.name:14} {how:24} config {checker.config}")
        return
    suite = Suite(checkers=CHECKERS, root=LAYOUT.root)
    sys.exit(suite.run(args.positional() or list(DEFAULT_PATHS)))


if __name__ == "__main__":
    main()
