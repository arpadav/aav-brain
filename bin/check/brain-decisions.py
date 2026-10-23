#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-decisions: question the brain's PAST decisions instead of confirming them.

every other scan check measures conformance to a decision already made - drift
against a build, lint against a config, shape against shape.toml. none of them
asks whether the decision itself still holds, and a config can hide the very
thing it should report (shape.toml once excluded every generated file from
shape). this tool asks three such questions, each derived from the code, never
from a hand-kept list:

- generated: which TRACKED files a builder in bin/ writes, or that .gitignore
  already disowns - and whether shape.toml states why each is committed
- reach: how many files outside a unit (skill, agent, flow state, principle
  card) name it - the cost of every past decision to extend it in place
- untraced: decision-making skills (the entries plus every flow-state owner)
  that never logged a fork to the decision trace (CONSTITUTION)

    python3 brain-decisions.py                       all three questions
    python3 brain-decisions.py generated|reach|untraced [...]   only those

exits non-zero when any question has a finding

Author: aav
"""
# brainlib lives in bin/, one folder up
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, DataLayout, Exit, Flow, Layout, Ledger, git, read_text

# --------------------------------------------------
# external
# --------------------------------------------------
import ast
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from types import SimpleNamespace

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem

# every path inside the brain, spelled once (brainlib.Layout)
LAYOUT = Layout.discover()

# the base class every committed, drift-checked builder subclasses (brainlib.model)
ARTIFACT_BASE = "Artifact"

# the builder method whose returned (path, content) pairs ARE its outputs
TARGETS_METHOD = "targets"

# the attribute a builder writes a whole directory through
OUT_DIR = "out_dir"


class Question(StrEnum):
    """the questions this tool asks, named once; each is also its subcommand."""

    GENERATED = "generated"
    REACH = "reach"
    UNTRACED = "untraced"


@dataclass(frozen=True)
class Policy:
    """the authored half of these questions, read from shape.toml `[decisions]`.

    `reasons` maps a tracked generated path to WHY it is committed; a path with
    no entry is a finding. `reach_files` is the threshold past which a unit is
    named from too many places
    """

    reasons: dict[str, str]
    reach_files: int

    @classmethod
    def load(cls, path: Path) -> "Policy":
        """read the `[decisions]` table.

        # Arguments

        * `path` - the shape.toml path

        # Returns

        the policy; a missing or malformed table is reported on stderr and
        yields no reasons and a threshold of 1, so it over-reports, never hides
        """
        try:
            table = tomllib.loads(read_text(path)).get("decisions", {})
            return cls({str(k): str(v) for k, v in table.get("tracked", {}).items()},
                       max(1, int(table["reach_files"])))
        except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError, ValueError, AttributeError) as broken:
            print(f"{TOOL}: no usable [decisions] in {path.name} ({broken}); every finding reported", file=sys.stderr)
            return cls({}, 1)


@dataclass(frozen=True)
class Output:
    """one thing a builder writes: an exact file, or every file under a directory."""

    path: str
    builder: str
    tree: bool

    def owns(self, tracked: str) -> bool:
        """whether this output covers a tracked path.

        # Arguments

        * `tracked` - a repo-relative posix path

        # Returns

        true for the exact file, or for anything under a directory output
        """
        return tracked == self.path or (self.tree and tracked.startswith(f"{self.path}/"))


@dataclass
class Builders:
    """every builder output, read off the builder SOURCE rather than listed by hand.

    a builder is a class subclassing `Artifact`; its outputs are the first
    element of each (path, content) pair its `targets` returns, evaluated
    against the Layout. a `targets` that writes through `self.out_dir` owns
    that whole directory, resolved from the `out_dir=` its constructor call
    passes. an expression that does not resolve inside the repo is skipped,
    because a file outside the repo is not a tracked-file question
    """

    root: Path
    outputs: list[Output] = field(default_factory=list)

    @classmethod
    def derive(cls, layout: Layout) -> "Builders":
        """parse every bin/ tool and collect its builders' outputs.

        # Arguments

        * `layout` - the brain layout the expressions are evaluated against

        # Returns

        the derived outputs
        """
        builders = cls(layout.root)
        for script in sorted(layout.bin.rglob("*.py")):
            if "brainlib" in script.parts:
                continue
            builders.read(script, ast.parse(read_text(script)), {"LAYOUT": layout, "Path": Path})
        return builders

    def read(self, script: Path, module: ast.Module, scope: dict[str, object]) -> None:
        """collect one module's builder outputs.

        # Arguments

        * `script` - the module's path, for the builder label
        * `module` - its parsed tree
        * `scope` - the names an output expression may reference; grown with
          each module-level constant that itself resolves
        """
        for statement in module.body:
            if (
                isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and (value := self.resolve(statement.value, scope)) is not None
            ):
                scope[statement.targets[0].id] = value
        for node in ast.walk(module):
            if not isinstance(node, ast.ClassDef) or not any(
                isinstance(base, ast.Name) and base.id == ARTIFACT_BASE for base in node.bases
            ):
                continue
            label = f"{script.stem}.{node.name}"
            for method in node.body:
                if not isinstance(method, ast.FunctionDef) or method.name != TARGETS_METHOD:
                    continue
                for out_dir in self.out_dirs(module, node.name, scope):
                    bound = {**scope, "self": SimpleNamespace(out_dir=out_dir)}
                    if not self.method(method, label, bound) and self.writes_out_dir(method):
                        self.add(out_dir, label, tree=True)

    def method(self, method: ast.FunctionDef, label: str, scope: dict[str, object]) -> bool:
        """record every exact path a `targets` method returns.

        # Arguments

        * `method` - the `targets` definition
        * `label` - the builder, for the report
        * `scope` - the names its expressions may reference, `self.out_dir` bound

        # Returns

        true when at least one returned path resolved; false means the paths
        are computed (a loop over sources), so the builder owns its out_dir whole
        """
        resolved = False
        for node in ast.walk(method):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.List | ast.Tuple):
                for pair in node.value.elts:
                    if isinstance(pair, ast.Tuple) and pair.elts:
                        value = self.resolve(pair.elts[0], scope)
                        resolved |= isinstance(value, Path)
                        self.add(value, label, tree=False)
        return resolved

    @staticmethod
    def writes_out_dir(method: ast.FunctionDef) -> bool:
        """whether a `targets` method builds its paths from `self.out_dir`.

        # Arguments

        * `method` - the `targets` definition

        # Returns

        true when `self.out_dir` appears anywhere in it
        """
        return any(
            isinstance(node, ast.Attribute) and node.attr == OUT_DIR
            and isinstance(node.value, ast.Name) and node.value.id == "self"
            for node in ast.walk(method)
        )

    def out_dirs(self, module: ast.Module, name: str, scope: dict[str, object]) -> list[object | None]:
        """the `out_dir=` of every constructor call of one builder class.

        # Arguments

        * `module` - the module the builder is defined in
        * `name` - the builder class name
        * `scope` - the names the keyword's expression may reference

        # Returns

        each resolved out_dir; one None when the class is never constructed
        here, so its literal LAYOUT targets are still read
        """
        found = [
            self.resolve(keyword.value, scope)
            for node in ast.walk(module)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name
            for keyword in node.keywords
            if keyword.arg == OUT_DIR
        ]
        return found or [None]

    @staticmethod
    def resolve(expr: ast.expr, scope: dict[str, object]) -> object | None:
        """evaluate a path expression against the names in scope only.

        no builtins are exposed: the expression is a Layout property, a `/`
        join of literals, or a constant built from those - anything else fails
        to evaluate and is skipped

        # Arguments

        * `expr` - the expression node
        * `scope` - the permitted names

        # Returns

        the value, or None when it does not evaluate
        """
        try:
            value: object = eval(compile(ast.Expression(expr), TOOL, "eval"), {"__builtins__": {}}, dict(scope))  # noqa: S307 - no builtins, a scope of Layout and Path only
        except Exception:  # noqa: BLE001 - any unresolvable expression is simply not a path output
            return None
        return value

    def add(self, value: object | None, label: str, *, tree: bool) -> None:
        """keep one resolved output if it lies inside the repo.

        # Arguments

        * `value` - the evaluated expression
        * `label` - the builder
        * `tree` - whether it is a directory output
        """
        if isinstance(value, Path) and value.is_relative_to(self.root):
            self.outputs.append(Output(value.relative_to(self.root).as_posix(), label, tree))

    def writer(self, tracked: str) -> str | None:
        """the builder that writes a tracked path, if any.

        # Arguments

        * `tracked` - a repo-relative posix path

        # Returns

        the builder label, or None
        """
        return next((out.builder for out in self.outputs if out.owns(tracked)), None)


@dataclass
class Questions:
    """the brain's past decisions, asked again; findings accumulate per question."""

    layout: Layout
    policy: Policy
    builders: Builders
    flow: Flow
    findings: int = 0

    def tracked(self, *extra: str) -> list[str]:
        """the tracked paths, refusing rather than reporting an empty repo.

        # Arguments

        * `extra` - further `git ls-files` arguments

        # Returns

        the repo-relative paths
        """
        listed = git(self.layout.root, "ls-files", "-z", *extra)
        if listed is None:
            print(f"{TOOL}: cannot list {self.layout.root}; refusing to report a clean scan", file=sys.stderr)
            sys.exit(Exit.USAGE)
        return [name for name in listed.split("\0") if name]

    def generated(self) -> None:
        """report every tracked file a builder writes or .gitignore disowns, and its stated reason."""
        ignored = set(self.tracked("--cached", "--ignored", "--exclude-standard"))
        for path in self.tracked():
            writer = self.builders.writer(path)
            if writer is None and path not in ignored:
                continue
            why = f"written by {writer}" if writer else "tracked but gitignored"
            if path in ignored and writer:
                why += ", and gitignored"
            reason = self.policy.reasons.get(path)
            if reason is None:
                self.findings += 1
            print(f"  generated  {path}  {why} - {reason or 'NO STATED REASON (shape.toml [decisions.tracked])'}")

    def units(self) -> Iterator[tuple[str, str, tuple[str, ...], str]]:
        """every unit whose reach is measured.

        # Returns

        (kind, unit, names it is spelled by, home path prefix) per unit; the
        home is excluded from its own count
        """
        root = self.layout.root
        for skill in sorted(p for p in self.layout.skills.iterdir() if p.is_dir()):
            yield "skill", skill.name, (skill.name,), f"{skill.relative_to(root).as_posix()}/"
        for agent in sorted(self.layout.agents.rglob("*.md")):
            yield "agent", agent.stem, (agent.stem,), agent.relative_to(root).as_posix()
        for state in self.flow.states:
            yield "state", state, (state,), f"{self.layout.flow_dir.relative_to(root).as_posix()}/"
        for card in sorted(self.layout.principles.glob("principle-*.md")):
            number = card.stem.split("-")[1]
            yield "card", card.stem, (card.stem, f"P{number}"), card.relative_to(root).as_posix()

    def reach(self) -> None:
        """report each unit named from more files outside it than the threshold allows."""
        rows: list[tuple[int, str, str]] = []
        for kind, unit, names, home in self.units():
            patterns = [arg for name in names for arg in ("-e", name)]
            listed = git(self.layout.root, "grep", "-l", "-w", "-F", *patterns)
            naming = [
                path for path in (listed or "").splitlines()
                if not path.startswith(home) and self.builders.writer(path) is None
            ]
            if len(naming) > self.policy.reach_files:
                rows.append((len(naming), kind, unit))
        for count, kind, unit in sorted(rows, reverse=True):
            print(f"  reach  {kind:<5}  {unit}  named in {count} file(s) outside it (limit {self.policy.reach_files})")
        self.findings += len(rows)

    def untraced(self) -> None:
        """report decision-making skills with no fork in the trace, live or pruned."""
        owners = {
            owner.strip().split(":")[0] for state in self.flow.states.values() for owner in state.owner.split("+")
        }
        skills = {p.name for p in self.layout.skills.iterdir() if p.is_dir()}
        deciders = (owners | {entry.skill for entry in self.flow.entries}) & skills
        traced = {row.get("skill") for row in Ledger(DataLayout.discover().decisions).read() if row.get("against")}
        for skill in sorted(deciders - traced):
            print(f"  untraced  {skill}  owns a decision but never logged a fork")
            self.findings += 1


def main() -> None:
    """ask the named questions (all of them by default) and exit non-zero on a finding."""
    args = Args.from_argv()
    args.gate(TOOL, __doc__)
    try:
        asked = [Question(name) for name in args.positional()] or list(Question)
    except ValueError as unknown:
        print(f"{TOOL}: {unknown}; expected one of {', '.join(Question)}", file=sys.stderr)
        sys.exit(Exit.USAGE)
    flow = Flow.load(LAYOUT.flow_toml)
    questions = Questions(LAYOUT, Policy.load(LAYOUT.shape_toml), Builders.derive(LAYOUT), flow)
    for question in asked:
        before = questions.findings
        getattr(questions, question.value)()
        print(f"{TOOL}: {question.value}: {questions.findings - before} finding(s)")
    if questions.findings:
        sys.exit(Exit.DRIFT)


if __name__ == "__main__":
    main()
