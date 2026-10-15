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
from brainlib import PYTHON_VERSION, Args, Flag, Layout, read_text

# --------------------------------------------------
# external
# --------------------------------------------------
import os
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
# every tree of this repo's own python. eval/ is here because a tool that is not
# linted is a tool held to a different bar than the one it measures
DEFAULT_PATHS = ("bin", "eval")
# the PEP-723 inline metadata block, and the requirement strings inside its
# `dependencies` list - a script declares here what it needs to import, and a
# checker that never installs them reports every one of those imports unresolved
SCRIPT_BLOCK = re.compile(r"^# /// script\n(?P<body>(?:^#.*\n)+?)^# ///$", re.MULTILINE)
# the closing bracket is the LAST one, not the first: a requirement carrying
# extras ("pydantic[email]") holds a `]` of its own, and a lazy match ends the
# list there and reports zero dependencies for a script that declared several
DECLARED = re.compile(r"dependencies\s*=\s*\[(?P<items>.*)\]", re.DOTALL)
REQUIREMENT = re.compile(r"[\"\']([^\"\']+)[\"\']")


@dataclass(frozen=True)
class Target:
    """the paths one run checks, and everything a checker must be told about them.

    a checker inherits NONE of this from its config file. a config pins the
    RULES, which are this repo's opinion and travel; where the code lives and
    what it imports belong to the code being checked, and a config that names
    them makes every run measure this repo whatever it was pointed at

    # Example

        target = Target(paths=("bin",), root=find_brain())
        target.search_paths      # the one directory bin/ scripts import from
    """

    paths: Sequence[str]
    root: Path

    @property
    def files(self) -> tuple[Path, ...]:
        """every python file this run covers, with directories expanded.

        # Returns

        one absolute path per file, sorted
        """
        found: list[Path] = []
        for raw in self.paths:
            path = self.root / raw
            found.extend(sorted(path.rglob("*.py")) if path.is_dir() else [path])
        return tuple(found)

    @property
    def search_paths(self) -> tuple[str, ...]:
        """the directories a checked file imports its siblings from.

        a script is not a package: it reaches the modules beside it through its
        own directory on `sys.path`, so a checker has to be told the same thing -
        per run, from the paths given, never from a relative entry in a config
        that a foreign script re-resolves against itself

        a directory holding an `__init__.py` IS a package and is deliberately
        excluded: its modules are reached through their parent as `pkg.module`,
        and offering the package directory as a second search root makes a
        checker find each file twice, under two module names, which mypy reports
        as an error before it checks anything at all

        # Returns

        one absolute directory per distinct parent, sorted, packages excluded
        """
        parents = {path.parent for path in self.files}
        return tuple(sorted(str(parent) for parent in parents
                            if not (parent / "__init__.py").is_file()))

    @property
    def dependencies(self) -> tuple[str, ...]:
        """every distribution the checked scripts declare in a PEP-723 header.

        an import a checker cannot resolve is a statement about the checker's
        environment, not about the code, and it crowds out the diagnostics that
        are about the code

        # Returns

        the requirement strings, deduplicated and sorted
        """
        found: set[str] = set()
        for path in self.files:
            block = SCRIPT_BLOCK.search(read_text(path)) if path.is_file() else None
            declared = DECLARED.search(block.group("body")) if block else None
            if declared:
                found.update(REQUIREMENT.findall(declared.group("items")))
        return tuple(sorted(found))


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
    # the flag that puts one directory on this checker's import search path;
    # empty where the checker takes no such flag
    search_flag: str = ""
    # the environment variable that does the same job for a checker with no flag
    search_env: str = ""
    # doctest takes files, not directories, so its paths are expanded first
    expands_dirs: bool = False

    def resolve(self, target: Target) -> list[str]:
        """every argument after the subcommand: search paths, then the paths.

        # Arguments
        * `target` - the paths this run checks and what they import from

        # Returns
        the search-path flags this checker understands, then the paths it takes,
        with directories expanded where the checker cannot walk one itself
        """
        out = [arg for path in target.search_paths for arg in (self.search_flag, path)
               if self.search_flag]

        if not self.takes_paths:
            return out
        if not self.expands_dirs:
            return out + list(target.paths)
        return out + [str(f) for f in target.files]

    def environment(self, target: Target) -> dict[str, str]:
        """the environment this checker runs in, over the caller's own.

        mypy takes its search path from `MYPYPATH` and has no flag for it, so a
        checker that names one gets it here rather than in the argv

        # Arguments
        * `target` - the paths this run checks and what they import from

        # Returns
        the full environment, with the search variable set where one is named
        """
        if not self.search_env:
            return dict(os.environ)
        return {**os.environ, self.search_env: os.pathsep.join(target.search_paths)}

    def command(self, dependencies: Sequence[str] = ()) -> list[str] | None:
        """the argv prefix that runs this checker on this machine.

        # Arguments
        * `dependencies` - the requirements the checked scripts declare, put into
          the tool's environment so their imports resolve. only `uvx` can be
          handed them: a checker already on PATH runs in whatever environment it
          was installed into, and its unresolved imports are reported as they are
          rather than papered over

        # Returns
        the command as a list, or None when neither the tool nor uv is present
        """
        if self.module:
            return [sys.executable, "-m", self.module]
        if shutil.which(self.name):
            return [self.name]
        if shutil.which("uv"):
            fetched = [arg for dependency in dependencies for arg in ("--with", dependency)]
            return ["uvx", "--python", PYTHON_VERSION, *fetched, self.name]
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

    def run_one(self, checker: Checker, target: Target) -> Outcome:
        """run a single checker, streaming its own output.

        # Arguments
        * `checker` - the checker to run
        * `target` - the paths to check and what they import from

        # Returns
        an Outcome carrying the tool's exit code and its own total
        """
        # --------------------------------------------------
        # resolve the tool, or report it unreachable
        # --------------------------------------------------
        command = checker.command(target.dependencies)
        if command is None:
            return Outcome(checker=checker)
        # --------------------------------------------------
        # build the argv and echo it, so a run is reproducible from the log
        # --------------------------------------------------
        argv = command + list(checker.args) + checker.resolve(target)
        print(f"\n$ {' '.join(argv)}")
        # stderr is merged rather than suppressed: a checker that dies on a bad
        # config must be visible as a failure, not as a clean run (P36)
        # argv is built from this file's own CHECKERS table plus paths he typed;
        # nothing here is remote input, and shell=False keeps it an exec not a shell (S603)
        result = subprocess.run(argv, cwd=self.root, env=checker.environment(target),  # noqa: S603
                                capture_output=True, text=True, check=False)
        # --------------------------------------------------
        # surface the tool's own output, then carry its verdict back
        # --------------------------------------------------
        output = result.stdout + result.stderr
        print(output.rstrip() or "(no output)")
        return Outcome(checker=checker, command=argv, code=result.returncode, total=checker.total(output))

    def run(self, target: Target) -> int:
        """run every checker and summarise.

        # Arguments
        * `target` - the paths to check and what they import from

        # Returns
        the exit code: 1 if any reachable checker reported findings
        """
        # --------------------------------------------------
        # run every checker
        # --------------------------------------------------
        outcomes = [self.run_one(checker, target) for checker in self.checkers]
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
            total_re=r"Found (\d+) diagnostic", search_flag="--extra-search-path"),
    Checker(name="mypy", config="mypy.ini", args=("--config-file", "mypy.ini"),
            total_re=r"Found (\d+) error", search_env="MYPYPATH"),
    # basedpyright takes the files positionally, which overrides what the config
    # would have scanned; the search path it reads names a directory of this repo
    # that exists, so unlike ty's it cannot be re-resolved into a path that does not
    Checker(name="basedpyright", config="pyrightconfig.json", args=("--project", "."),
            total_re=r"(\d+) errors?,"),
    # the repo's only tests: the doctests carried by the pure helpers (aav-style-items §12)
    Checker(name="doctest", config="(inline)", args=(), total_re=r"\*\*\* (\d+) failures",
            module="doctest", expands_dirs=True),
)


def main() -> None:
    """run the suite, or list what is reachable."""
    args = Args.from_argv()
    args.gate(TOOL, __doc__, Flag.LIST)
    if args.has(Flag.LIST):
        for checker in CHECKERS:
            command = checker.command()
            how = " ".join(command) if command else "unreachable"
            print(f"  {checker.name:14} {how:24} config {checker.config}")
        return
    target = Target(paths=args.positional() or list(DEFAULT_PATHS), root=LAYOUT.root)
    sys.exit(Suite(checkers=CHECKERS, root=LAYOUT.root).run(target))


if __name__ == "__main__":
    main()
