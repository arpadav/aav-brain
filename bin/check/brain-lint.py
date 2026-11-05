#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""b-lint: run every python checker that is installed, against its pinned config.

    b-lint             check the configured paths
    b-lint bin/foo.py  check specific paths instead, relative to the brain root
    b-lint -l          show which checkers are reachable, run none
    b-lint -v          echo every checker's full command line

four checkers, four configs, one command. they do not overlap: ruff is a linter
and cannot see types at all - a bare `dict` annotation is invisible to every one
of its 956 rules - while ty, mypy and basedpyright each infer types and each
catches a slightly different slice. so the rule here is not "pick the best one",
it is RUN EVERY ONE THAT IS PRESENT. a checker that is not installed is reported
as skipped, never silently dropped, because a green run that quietly checked two
of four tools is the kind of false confidence this exists to prevent

each checker resolves the same way: use it directly if it is on PATH, else run
it through `uvx` if uv is there, else skip it and say so. a checker that exited
non-zero, findings or a crash, has its own output printed verbatim, in full; a
clean one's prints only under `--verbose`. the totals in the summary are the
ones the tool itself reported - this script never counts findings on a tool's
behalf

the summary names each checker, its verdict and its config. a checker's full
command line - the repo root it runs in, mypy's MYPYPATH, then the argv, which
for doctest names every file it checks - prints only for one that exited
non-zero, findings or a crash, so it can be pasted to rerun it; or for every
checker under `--verbose`

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import ENCODING, PYTHON_VERSION, Args, Exit, Flag, Layout, Tool, read_text

# --------------------------------------------------
# external
# --------------------------------------------------
import os
import re
import shlex
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages
TOOL = Layout.command(Path(__file__))
# every path this tool touches, resolved once by the shared discovery
LAYOUT = Layout.discover()
# what gets checked when no path is given on the command line
# every tree of this repo's own python. eval/ is here because a tool that is not
# linted is a tool held to a different bar than the one it measures, and
# agentic-files/ because a skill's script is a brain tool like any in bin/
DEFAULT_PATHS = ("bin", "eval", "agentic-files")
# the PEP-723 inline metadata block, and the requirement strings inside its
# `dependencies` list - a script declares here what it needs to import, and a
# checker that never installs them reports every one of those imports unresolved
SCRIPT_BLOCK = re.compile(r"^# /// script\n(?P<body>(?:^#.*\n)+?)^# ///$", re.MULTILINE)
# the closing bracket is the LAST one, not the first: a requirement carrying
# extras ("pydantic[email]") holds a `]` of its own, and a lazy match ends the
# list there and reports zero dependencies for a script that declared several
DECLARED = re.compile(r"dependencies\s*=\s*\[(?P<items>.*)\]", re.DOTALL)
# one quoted requirement inside the declared list, in either quote style
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
        target.search_paths      # bin/ and each script folder under it; brainlib, a package, is not one
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

        a script is not a package: it reaches the modules beside it through a
        directory on `sys.path` - its own dir by default, and under
        `python -I`, which leaves that off, the dir it inserts itself - so a
        checker has to be told the same thing: per run, from the paths given,
        never from a relative entry in a config that a foreign script
        re-resolves against itself

        a script anywhere in the brain inserts bin/ itself, however deep it
        sits (`bin/run/brain-walk.py`, `eval/brain-eval.py` and a skill's script
        reach brainlib that way), so bin/ is a search root whenever a checked
        file lies in the brain, and never for a file outside it, which a run
        names by its absolute path

        a directory holding an `__init__.py` IS a package and is deliberately
        excluded: its modules are reached through their parent as `pkg.module`,
        and offering the package directory as a second search root makes a
        checker find each file twice, under two module names, which mypy reports
        as an error before it checks anything at all

        # Returns

        one absolute directory per distinct parent, plus bin/ for a file in the
        brain, sorted, packages excluded

        # Example

            >>> Target(paths=("bin/run/brain-walk.py",), root=Path("/r")).search_paths
            ('/r/bin', '/r/bin/run')
            >>> Target(paths=("eval/brain-eval.py",), root=Path("/r")).search_paths
            ('/r/bin', '/r/eval')
            >>> Target(paths=("/elsewhere/x.py",), root=Path("/r")).search_paths
            ('/elsewhere',)
        """
        brain_bin = Layout(self.root).bin
        parents = {path.parent for path in self.files}
        parents |= {brain_bin} if any(path.is_relative_to(self.root) for path in self.files) else set()
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

    def rerun(self, argv: Sequence[str], target: Target) -> str:
        """one shell line that reruns this checker as brain-lint ran it, from any cwd.

        # Arguments
        * `argv` - the full argv brain-lint ran
        * `target` - the paths checked, whose root is the cwd and whose search paths fill `search_env`

        # Returns
        `cd <root> && [VAR=<paths>] <argv>`, every part shell-quoted

        # Example

            >>> mypy = Checker(name="mypy", config="mypy.ini", args=(), total_re="", search_env="MYPYPATH")
            >>> mypy.rerun(["mypy", "bin/x y.py"], Target(paths=("bin/x y.py",), root=Path("/r")))
            "cd /r && MYPYPATH=/r/bin mypy 'bin/x y.py'"
        """
        variable = f"{self.search_env}={shlex.quote(os.pathsep.join(target.search_paths))} " if self.search_env else ""
        return f"cd {shlex.quote(str(target.root))} && {variable}{shlex.join(argv)}"

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
    # the shell line that reruns it (`Checker.rerun`); None when it never ran
    command: str | None = None
    code: int | None = None
    total: int | None = None

    @property
    def skipped(self) -> bool:
        """whether the checker could not be reached at all.

        # Returns
        true when neither the tool nor uv was found
        """
        return self.command is None

    def summary(self, *, verbose: bool = False) -> str:
        """this checker's summary: its name, verdict and config, and its command when wanted.

        the command follows on a second line for a checker that exited
        non-zero (findings, or a crash), so it can be pasted to rerun it, and
        for every checker under `verbose`

        # Arguments

        * `verbose` - add the command under a clean checker too

        # Returns

        one line - skipped, clean, or the finding count - then the command's
        line when it is wanted

        # Example

            >>> ruff = Checker(name="ruff", config="ruff.toml", args=(), total_re="")
            >>> print(Outcome(ruff, "cd /r && ruff check bin", 0).summary())
              ruff           clean      config ruff.toml
            >>> print(Outcome(ruff, "cd /r && ruff check bin", 1, 3).summary())
              ruff              3 FOUND config ruff.toml
                via `cd /r && ruff check bin`
            >>> print(Outcome(ruff).summary(verbose=True))
              ruff           SKIPPED    not installed, and uv is not available to fetch it
        """
        # --------------------------------------------------
        # a checker that never ran has no verdict and no command
        # --------------------------------------------------
        if self.command is None:
            return f"  {self.checker.name:14} {'SKIPPED':10} not installed, and uv is not available to fetch it"
        # --------------------------------------------------
        # the verdict and config, then the command when it failed or is asked for
        # --------------------------------------------------
        count = "?" if self.total is None else str(self.total)
        verdict = "clean" if self.code == 0 else f"{count:>4} FOUND"
        line = f"  {self.checker.name:14} {verdict:10} config {self.checker.config}"
        return f"{line}\n    via `{self.command}`" if verbose or self.code != 0 else line


@dataclass
class Suite:
    """every checker, run against one set of paths."""

    checkers: Sequence[Checker]
    # echo every checker's full command, not only a failed one's
    verbose: bool = False

    def run_one(self, checker: Checker, target: Target) -> Outcome:
        """run a single checker, printing its own output when it exited non-zero or under verbose.

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
        # build the argv; it heads the output under verbose, and the summary repeats a failed one's
        # --------------------------------------------------
        argv = command + list(checker.args) + checker.resolve(target)
        rerun = checker.rerun(argv, target)
        # stderr is merged rather than suppressed: a checker that dies on a bad
        # config must be visible as a failure, not as a clean run (P36). a byte
        # that is not utf-8 prints as a replacement character, never a crash
        # argv is built from this file's own CHECKERS table plus paths he typed;
        # nothing here is remote input, and shell=False keeps it an exec not a shell (S603)
        result = subprocess.run(argv, cwd=target.root, env=checker.environment(target),  # noqa: S603
                                capture_output=True, encoding=ENCODING, errors="replace", check=False)
        # --------------------------------------------------
        # a failed checker's own output in full, a clean one's only under verbose; then its verdict
        # --------------------------------------------------
        output = result.stdout + result.stderr
        if self.verbose or result.returncode != 0:
            print(f"$ {rerun}" if self.verbose else f"== {checker.name}")
            print(f"{output.rstrip() or '(no output)'}\n")
        return Outcome(checker=checker, command=rerun, code=result.returncode, total=checker.total(output))

    def run(self, target: Target) -> Exit:
        """run every checker and summarise.

        # Arguments
        * `target` - the paths to check and what they import from

        # Returns
        FINDINGS if any reachable checker reported findings, else OK
        """
        # --------------------------------------------------
        # run every checker
        # --------------------------------------------------
        outcomes = [self.run_one(checker, target) for checker in self.checkers]
        # --------------------------------------------------
        # report one line per checker
        # --------------------------------------------------
        print(f"{TOOL}:")
        for outcome in outcomes:
            print(outcome.summary(verbose=self.verbose))
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
            return Exit.FINDINGS
        print(f"  all {len(ran)} reachable checker(s) clean")
        return Exit.OK

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
    # the doctests carried by the pure helpers (aav-style-items §12)
    Checker(name="doctest", config="(inline)", args=(), total_re=r"\*\*\* (\d+) failures",
            module="doctest", expands_dirs=True),
)


def main(args: Args) -> Exit:
    """run the suite, or list what is reachable.

    # Arguments

    * `args` - the parsed command line; `--list` prints each checker and how it
      is invoked instead of running, `--verbose` echoes every checker's full
      command, positionals are the paths to check

    # Returns

    `Exit.OK` after a listing, else the suite's own status over the target
    """
    if args.has(Flag.LIST):
        width = max(len(str(checker.config)) for checker in CHECKERS)
        for checker in CHECKERS:
            command = checker.command()
            how = " ".join(command) if command else "unreachable"
            print(f"  {checker.name:14} config {checker.config!s:{width}} {how}")
        return Exit.OK
    target = Target(paths=args.positional() or list(DEFAULT_PATHS), root=LAYOUT.root)
    return Suite(checkers=CHECKERS, verbose=args.has(Flag.VERBOSE)).run(target)


if __name__ == "__main__":
    # a listing starts no checker, so it has none to echo
    Tool.of(TOOL, __doc__, positionals=(0, None), modes=((Flag.LIST,), (Flag.VERBOSE,))).run(main)
