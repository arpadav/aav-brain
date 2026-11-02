#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-eval: does a brain version actually change how the work comes out.

a public coding benchmark scores `model + harness + context` jointly, and model
variance dominates - so a leaderboard number cannot tell you whether the cards
work. this measures the only thing a context layer can be credited with: whether
the brain's own rules landed in the output.

the design is PAIRED. the same task runs twice against the same model, once with
the brain's context and once without, and the two are compared per task rather
than as two aggregate scores. that removes the model from the comparison, which
is the whole difficulty.

criteria are BINARY and card-derived. binary judgements agree between graders
because there is no boundary to argue over; gradation comes from the weighted
composite. every criterion names the card it came from, so a rule that stops
mattering is traceable to the card that changed.

25 tasks over five categories - patch, zero-to-one, long-form, plan, review.
that is enough to see a graded effect and NOT enough to see a small binary one,
which is why nothing here is scored pass/fail. for the correctness axis, point a
public benchmark at it instead; this harness is for the axis no public benchmark
covers.

    python3 brain-eval.py tasks                 list the task set
    python3 brain-eval.py init  RUN             materialise fixtures for a run
    python3 brain-eval.py pack  RUN             write each task-arm's dispatch prompt
    python3 brain-eval.py collect RUN FILE      fold the agents' reports in
    python3 brain-eval.py sheet RUN             the grading sheet for a run
    python3 brain-eval.py score RUN             composite scores from a graded sheet
    python3 brain-eval.py report RUN [RUN...]   paired deltas across runs

Author: aav
"""
# brainlib lives in bin/, a sibling of this folder
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Env, Exit, Layout, Tool, UsageError, git, read_text, write_text

# --------------------------------------------------
# external
# --------------------------------------------------
import json
import os
import shutil
import statistics
import subprocess
import tomllib
from dataclasses import dataclass, field

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem

# every path inside the brain, spelled once
LAYOUT = Layout.discover()

# this harness's own tree, beside the tool
HERE = Path(__file__).resolve().parent

# where every run's tree lives; a run is one directory directly inside it
RUNS = HERE / "results"

# the two arms of every pair. `off` is the control: the same model and the same
# task with no brain context at all, which is what makes a difference
# attributable to the cards rather than to the model
ARMS = ("on", "off")

# `collect` is the one subcommand taking two positionals: the run and the file
COLLECT_ARGS = 2

# what a run's tree holds: its metadata and grading sheet at the root, and each
# task-arm's collected report in that task-arm's directory
RUN_META = "run.json"
SHEET = "SHEET.md"
REPORT = "REPORT.md"

# the sheet line that opens one arm's section, written by `sheet` and read back by `score`
ARM_HEADING = "# ARM: "


class RunError(UsageError):
    """a run name a subcommand cannot act on; its message names the run and why."""


@dataclass(frozen=True)
class Criterion:
    """one binary judgement, its weight, and the card it comes from."""

    key: str
    weight: int
    met: str
    card: str = ""

    def line(self) -> str:
        """this criterion as a grading-sheet entry.

        # Returns

        a markdown block with an unfilled verdict slot
        """
        origin = f"  _{self.card}_\n" if self.card else ""
        body = " ".join(self.met.split())
        return f"- [ ] **{self.key}** ({self.weight})\n{origin}  {body}\n"


@dataclass
class Task:
    """one task: its fixture, its prompt, and the criteria it is judged on."""

    id: str
    category: str
    title: str
    prompt: str
    fixture: dict[str, str] = field(default_factory=dict)
    criteria: list[Criterion] = field(default_factory=list)
    planted: str = ""

    def total(self) -> int:
        """the points available on this task.

        # Returns

        the sum of every criterion's weight
        """
        return sum(c.weight for c in self.criteria)


def load_tasks() -> list[Task]:
    """every task, with its category's shared criteria folded in.

    # Returns

    the tasks in category then file order

    # Example

        >>> len(load_tasks()) > 0
        True
    """
    # --------------------------------------------------
    # the criteria every task of a rubric group shares
    # --------------------------------------------------
    shared = tomllib.loads(read_text(HERE / "rubrics" / "shared.toml"))
    out: list[Task] = []
    for path in sorted((HERE / "tasks").glob("*.toml")):
        # --------------------------------------------------
        # one task file: its category, the groups it opts into, and its tasks
        # --------------------------------------------------
        spec = tomllib.loads(read_text(path))
        groups = spec.get("rubric_groups", [])
        # --------------------------------------------------
        # the shared criteria of the groups this file names
        # --------------------------------------------------
        common = [Criterion(key, body["weight"], body["met"], body.get("card", ""))
                  for group in groups for key, body in shared.get(group, {}).items()]
        for entry in spec.get("task", []):
            # --------------------------------------------------
            # a task's own criteria come first, then the shared ones
            # --------------------------------------------------
            extra = [Criterion(key, body["weight"], body["met"])
                     for key, body in entry.get("extra", {}).items()]
            out.append(Task(
                id=entry["id"], category=spec["category"], title=entry["title"],
                prompt=entry["prompt"].strip(), fixture=entry.get("fixture", {}),
                criteria=extra + common, planted=entry.get("planted", ""),
            ))
    return out


def brain_version() -> str:
    """the brain commit a run is attributable to.

    a score without one cannot be compared to anything later

    # Returns

    the short commit hash, with `-dirty` when the tree has uncommitted changes
    """
    # --------------------------------------------------
    # the commit the brain is at
    # --------------------------------------------------
    head = (git(LAYOUT.root, "rev-parse", "--short", "HEAD") or "unknown").strip()
    # --------------------------------------------------
    # uncommitted changes make it a different brain than that commit
    # --------------------------------------------------
    dirty = git(LAYOUT.root, "status", "--porcelain")
    return f"{head}-dirty" if dirty and dirty.strip() else head


def run_dir(run: str) -> Path:
    """where one run's fixtures, outputs and sheet live, refusing a name that escapes RUNS.

    `clean` removes this directory whole, so a name that resolves anywhere but
    one level inside RUNS - `..`, a nested or absolute path, a symlink out -
    raises instead of naming a tree to delete

    # Arguments

    * `run` - the run name

    # Returns

    `eval/results/<run>`, resolved; raises RunError for a name outside RUNS

    # Example

        >>> run_dir("r1") == RUNS.resolve() / "r1"
        True
        >>> try:
        ...     _ = run_dir("../..")
        ... except RunError as escaped:
        ...     str(escaped).startswith("run '../..' is not a directory directly inside")
        True
    """
    # --------------------------------------------------
    # a run is one directory directly inside the runs folder, never a path out of it
    # --------------------------------------------------
    root = RUNS.resolve()
    path = (root / run).resolve()
    if path.parent != root:
        raise RunError(f"run {run!r} is not a directory directly inside {root}")
    return path


def require_run(run: str) -> Path:
    """a run's tree, refusing a run `init` never created.

    # Arguments

    * `run` - the run name

    # Returns

    the run's directory; raises RunError when it holds no RUN_META
    """
    root = run_dir(run)
    # --------------------------------------------------
    # a folder without its metadata was never initialised
    # --------------------------------------------------
    if not (root / RUN_META).is_file():
        raise RunError(f"no run {run!r} - init it first")
    return root


def cmd_tasks() -> None:
    """print the task set with its point totals."""
    tasks = load_tasks()
    # --------------------------------------------------
    # group the tasks by category
    # --------------------------------------------------
    by_category: dict[str, list[Task]] = {}
    for task in tasks:
        by_category.setdefault(task.category, []).append(task)
    # --------------------------------------------------
    # one block per category
    # --------------------------------------------------
    for category, group in by_category.items():
        print(f"\n{category}  ({len(group)} tasks)")
        for task in group:
            print(f"  {task.id:<26} {len(task.criteria):>2} criteria, {task.total():>2} pts   {task.title}")
    # --------------------------------------------------
    # the totals
    # --------------------------------------------------
    print(f"\n{len(tasks)} tasks, {sum(t.total() for t in tasks)} points, "
          f"{len(by_category)} categories")


def cmd_init(run: str) -> None:
    """materialise every task fixture, twice, one arm each.

    both arms start from byte-identical fixtures - the ONLY difference between
    them is whether the brain's context reaches the agent

    # Arguments

    * `run` - the run name to create
    """
    root = run_dir(run)
    # --------------------------------------------------
    # a run is never overwritten
    # --------------------------------------------------
    if root.exists():
        raise RunError(f"{root} already exists; pick another run name")
    tasks = load_tasks()
    for task in tasks:
        for arm in ARMS:
            # --------------------------------------------------
            # each task-arm gets its own working directory
            # --------------------------------------------------
            work = root / arm / task.id
            work.mkdir(parents=True)
            # --------------------------------------------------
            # the task's fixture files, so the agent starts from the same files in both arms
            # --------------------------------------------------
            for name, body in task.fixture.items():
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                write_text(target, body.strip() + "\n")
            # --------------------------------------------------
            # the request itself
            # --------------------------------------------------
            write_text(work / "TASK.md", f"# {task.title}\n\n{task.prompt}\n")
    # --------------------------------------------------
    # the run's metadata, which pins the brain version it measured
    # --------------------------------------------------
    meta = {"run": run, "brain": brain_version(), "tasks": [t.id for t in tasks], "arms": list(ARMS)}
    write_text(root / RUN_META, json.dumps(meta, indent=1) + "\n")
    # --------------------------------------------------
    # tell the operator how to run it next
    # --------------------------------------------------
    print(f"{TOOL}: {len(tasks)} tasks x {len(ARMS)} arms -> {root}")
    print(f"{TOOL}: brain version {meta['brain']}")
    print(f"\nrun each `{root}/<arm>/<task>/TASK.md` with the agent, in that directory.")
    print("the `on` arm gets the brain; the `off` arm gets no brain context at all.")
    print(f"then: python3 {TOOL}.py sheet {run}")


def cmd_pack(run: str) -> None:
    """write each task-arm's exact dispatch prompt.

    the ONE difference between the arms is here: the `on` prompt carries what
    `brain-recall` returns for that task, the `off` prompt carries nothing. a
    dispatched agent inherits the global preamble either way and it cannot be
    stripped per agent - but it is identical in both arms, so it cancels in the
    paired difference. what varies between brain versions is the cards and the
    retrieval, which is what this isolates

    # Arguments

    * `run` - the run `init` created, to pack
    """
    root = require_run(run)
    packed = 0
    for task in load_tasks():
        for arm in ARMS:
            work = root / arm / task.id
            # --------------------------------------------------
            # the prompt, with the brain's recalled rules appended on the `on` arm only
            # --------------------------------------------------
            lines = [f"# {task.title}", "", task.prompt, ""]
            if arm == "on":
                cards = run_recall(task.prompt)
                lines += ["---", "", "## the rules that apply to this task", "",
                          "these came from the brain for this task. they are the standing rules",
                          "you work under - not part of the request.", "", cards, ""]
            lines += ["---", "",
                      "work in this directory. do not read or write outside it.",
                      "when you are done, report what is done and what is left."]
            # --------------------------------------------------
            # write the finished prompt
            # --------------------------------------------------
            write_text(work / "PROMPT.md", "\n".join(lines) + "\n")
            packed += 1
    print(f"{TOOL}: {packed} prompts -> {root}/<arm>/<task>/PROMPT.md")


def run_recall(prompt: str) -> str:
    """what the brain returns for one task prompt.

    # Arguments

    * `prompt` - the task text to recall against

    # Returns

    recall's stdout, or a note when it could not run or did not exit OK - never
    a silent empty string, which would make an `on` arm secretly an `off` arm
    """
    # --------------------------------------------------
    # recall runs as a child of this interpreter
    # --------------------------------------------------
    argv = [sys.executable, str(LAYOUT.recall_script)]
    # --------------------------------------------------
    # run recall on the task text; any failure becomes a bracketed note in the prompt, not a crash
    # --------------------------------------------------
    # each task goes to a fresh agent that never saw an earlier task's recall, so
    # recall must not shorten a card it printed for an earlier task in this session
    env = {k: v for k, v in os.environ.items() if k != Env.SESSION_ID}
    try:
        done = subprocess.run(argv, input=prompt, capture_output=True, text=True, check=False,  # noqa: S603
                              timeout=60, env=env)
    except (OSError, subprocess.SubprocessError) as broken:
        return f"[brain-recall could not run: {broken}]"
    if done.returncode != Exit.OK:
        return f"[brain-recall exited {done.returncode}: {done.stderr.strip()}]"
    return done.stdout.strip() or "[brain-recall returned nothing for this task]"


def cmd_collect(run: str, reports: Path) -> None:
    """fold the agents' final reports into the run, for grading.

    several criteria judge what the agent SAID, not what it wrote - whether it
    reported state or narrated a changelog, whether it asked or assumed. those
    are ungradeable from the working directory alone

    # Arguments

    * `run` - the run to collect into
    * `reports` - a json file of {"<arm>/<task id>": "<final report>"}

    raises RunError, writing nothing, for a run `init` never created, a file
    that is not such an object, or a key naming no task-arm of the run
    """
    root = require_run(run)
    try:
        # --------------------------------------------------
        # the reports file must read and parse
        # --------------------------------------------------
        payload = json.loads(read_text(reports))
    except (OSError, ValueError) as unreadable:
        raise RunError(f"cannot read {reports}: {unreadable}") from unreadable
    # --------------------------------------------------
    # it must be an object of task-arm to report
    # --------------------------------------------------
    match payload:
        case {**entries}:
            pass
        case _:
            raise RunError(f"{reports} holds a json {type(payload).__name__}, not an object of task-arm to report")
    # --------------------------------------------------
    # every key must name a task-arm of this run and carry text
    # --------------------------------------------------
    tasks = json.loads(read_text(root / RUN_META))["tasks"]
    known = {f"{arm}/{task}" for arm in ARMS for task in tasks}
    if stray := sorted(str(key) for key, text in entries.items() if key not in known or not isinstance(text, str)):
        raise RunError(f"{reports}: {', '.join(stray)} name no task-arm of run {run!r} or carry no text")
    # --------------------------------------------------
    # write each report where the sheet will look for it
    # --------------------------------------------------
    for key, text in entries.items():
        write_text(root / str(key) / REPORT, str(text).rstrip() + "\n")
    print(f"{TOOL}: {len(entries)} report(s) written into {root}")


def cmd_sheet(run: str) -> None:
    """write the grading sheet for a run.

    # Arguments

    * `run` - the run to build a sheet for
    """
    root = require_run(run)
    tasks = load_tasks()
    # --------------------------------------------------
    # the sheet header and the grading rules
    # --------------------------------------------------
    out = [f"# grading sheet - run `{run}`, brain `{json.loads(read_text(root / RUN_META))['brain']}`\n",
           "tick a box when the criterion is MET. leave it unticked when it is not.\n",
           "grade one ARM at a time and do not look at the other while you do - the",
           "comparison is the measurement, so knowing which arm you are grading is",
           "the one thing that biases it.\n"]
    for arm in ARMS:
        # --------------------------------------------------
        # one section per arm, each task with its criteria as checkboxes
        # --------------------------------------------------
        out.append(f"\n---\n\n{ARM_HEADING}{arm}\n")
        for task in tasks:
            out.append(f"\n## {task.id} - {task.title}\n")
            work = root / arm / task.id
            out.append(f"`{work}`\n")
            # --------------------------------------------------
            # what the agent reported, and the planted defect for the grader
            # --------------------------------------------------
            report = work / REPORT
            if report.is_file():
                said = read_text(report).strip()
                out.append(f"\n<details><summary>what it reported</summary>\n\n{said}\n\n</details>\n")
            if task.planted:
                out.append(f"\n> planted defect (grader only): {task.planted}\n")
            out.append("")
            out.extend(c.line() for c in task.criteria)
    # --------------------------------------------------
    # write the sheet and say what it holds
    # --------------------------------------------------
    write_text(root / SHEET, "\n".join(out))
    print(f"{TOOL}: {root / SHEET}")
    print(f"{TOOL}: {len(tasks) * len(ARMS)} task-arms, "
          f"{sum(len(t.criteria) for t in tasks) * len(ARMS)} judgements")


def parse_sheet(path: Path) -> dict[tuple[str, str], set[str]]:
    """the ticked criteria, keyed by (arm, task).

    # Arguments

    * `path` - the graded SHEET

    # Returns

    a mapping from (arm, task id) to the set of MET criterion keys
    """
    # --------------------------------------------------
    # read the sheet line by line, tracking the current arm and task
    # --------------------------------------------------
    met: dict[tuple[str, str], set[str]] = {}
    arm = ""
    task = ""
    for line in read_text(path).splitlines():
        if line.startswith(ARM_HEADING):
            arm = line.removeprefix(ARM_HEADING).strip()
        elif line.startswith("## "):
            task = line.removeprefix("## ").split(" - ")[0].strip()
            met.setdefault((arm, task), set())
        elif line.strip().startswith("- [x]") or line.strip().startswith("- [X]"):
            key = line.split("**")[1] if "**" in line else ""
            if key and arm and task:
                met.setdefault((arm, task), set()).add(key)
    return met


def cmd_score(run: str) -> None:
    """turn a graded sheet into per-task composite scores.

    # Arguments

    * `run` - the graded run
    """
    root = require_run(run)
    # --------------------------------------------------
    # the sheet must exist
    # --------------------------------------------------
    sheet = root / SHEET
    if not sheet.is_file():
        raise RunError(f"no sheet for {run!r}")
    # --------------------------------------------------
    # read the ticks, then score each task as the ticked share of its weight, per arm
    # --------------------------------------------------
    met = parse_sheet(sheet)
    tasks = {t.id: t for t in load_tasks()}
    scored: dict[str, dict[str, float]] = {arm: {} for arm in ARMS}
    for (arm, task_id), keys in met.items():
        task = tasks.get(task_id)
        if task is None or arm not in scored:
            continue
        earned = sum(c.weight for c in task.criteria if c.key in keys)
        scored[arm][task_id] = earned / task.total() if task.total() else 0.0
    meta = json.loads(read_text(root / RUN_META))
    # --------------------------------------------------
    # store the scores in the run's metadata
    # --------------------------------------------------
    meta["scores"] = scored
    write_text(root / RUN_META, json.dumps(meta, indent=1) + "\n")
    for arm in ARMS:
        # --------------------------------------------------
        # the mean per arm
        # --------------------------------------------------
        values = list(scored[arm].values())
        if values:
            print(f"{TOOL}: {arm:<4} {len(values):>2} tasks graded, mean {statistics.mean(values):.3f}")
    if not any(scored[arm] for arm in ARMS):
        print(f"{TOOL}: nothing ticked yet - grade {sheet} first")


def cmd_report(runs: list[str]) -> None:
    """the paired comparison, per category and overall.

    reported as a paired difference because that is the only form that removes
    the model: the same task, the same model, brain on minus brain off

    # Arguments

    * `runs` - the scored runs to report
    """
    tasks = {t.id: t for t in load_tasks()}
    # --------------------------------------------------
    # the table header
    # --------------------------------------------------
    print(f"{'run':<14}{'brain':<14}{'n':>4}{'on':>8}{'off':>8}{'paired d':>10}{'wins':>7}{'losses':>8}")
    print("-" * 73)
    for run in runs:
        # --------------------------------------------------
        # one row per run, over the tasks both arms were scored on
        # --------------------------------------------------
        meta = json.loads(read_text(require_run(run) / RUN_META))
        scored = meta.get("scores", {})
        paired = [(scored.get("on", {}).get(tid), scored.get("off", {}).get(tid))
                  for tid in tasks if tid in scored.get("on", {}) and tid in scored.get("off", {})]
        # --------------------------------------------------
        # a run with nothing scored has no row
        # --------------------------------------------------
        if not paired:
            print(f"{run:<14}{meta.get('brain', '?'):<14}(not scored)")
            continue
        # --------------------------------------------------
        # the paired differences and the row
        # --------------------------------------------------
        deltas = [on - off for on, off in paired]
        wins = sum(1 for d in deltas if d > 0)
        losses = sum(1 for d in deltas if d < 0)
        print(f"{run:<14}{meta.get('brain', '?'):<14}{len(paired):>4}"
              f"{statistics.mean(o for o, _ in paired):>8.3f}"
              f"{statistics.mean(f for _, f in paired):>8.3f}"
              f"{statistics.mean(deltas):>+10.3f}{wins:>7}{losses:>8}")
        # --------------------------------------------------
        # the standard error of the paired difference, against the noise floor
        # --------------------------------------------------
        if len(deltas) > 1:
            spread = statistics.stdev(deltas) / (len(deltas) ** 0.5)
            print(f"{'':<28}standard error {spread:.3f} - a difference under "
                  f"{2 * spread:.3f} is not distinguishable from noise at this n")
    # --------------------------------------------------
    # what the columns mean, and what this n can resolve
    # --------------------------------------------------
    print("\npaired d is the mean of (on - off) per task, not the difference of two means.")
    print("25 tasks resolves a graded effect; it does NOT resolve a small binary one.")


def cmd_clean(run: str) -> None:
    """delete a run's tree.

    # Arguments

    * `run` - the run to remove
    """
    root = require_run(run)
    # --------------------------------------------------
    # delete the run tree
    # --------------------------------------------------
    shutil.rmtree(root)
    print(f"{TOOL}: removed {root}")


def main(args: Args) -> None:
    """dispatch the requested subcommand.

    `tasks` lists the tasks; `init`, `pack`, `sheet`, `score` and `clean` each
    take one run; `collect` takes a run and a file; `report` takes one or more runs

    # Arguments

    * `args` - the parsed command line; the first positional is the subcommand
      and the rest are its operands

    # Raises

    UsageError for an unknown subcommand or one missing its operands
    """
    # --------------------------------------------------
    # the subcommand and its arguments
    # --------------------------------------------------
    command, *names = args.positional()
    per_run = {"init": cmd_init, "pack": cmd_pack, "sheet": cmd_sheet, "score": cmd_score, "clean": cmd_clean}
    # --------------------------------------------------
    # dispatch: a command needs the arguments its own handler takes
    # --------------------------------------------------
    if command == "tasks":
        cmd_tasks()
    elif command in per_run and names:
        per_run[command](names[0])
    elif command == "collect" and len(names) == COLLECT_ARGS:
        cmd_collect(names[0], Path(names[1]))
    elif command == "report" and names:
        cmd_report(names)
    else:
        raise UsageError(f"unknown or incomplete command {command!r}")


if __name__ == "__main__":
    Tool(TOOL, __doc__, positionals=(1, None)).run(main)
