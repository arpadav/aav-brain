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
from brainlib import Args, Exit, Flag, Layout, git, read_text, write_text

# --------------------------------------------------
# external
# --------------------------------------------------
import json
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

# the two arms of every pair. `off` is the control: the same model and the same
# task with no brain context at all, which is what makes a difference
# attributable to the cards rather than to the model
ARMS = ("on", "off")

# `collect` is the one subcommand taking two positionals: the run and the file
COLLECT_ARGS = 2


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
    shared = tomllib.loads(read_text(HERE / "rubrics" / "shared.toml"))
    out: list[Task] = []
    for path in sorted((HERE / "tasks").glob("*.toml")):
        spec = tomllib.loads(read_text(path))
        groups = spec.get("rubric_groups", [])
        common = [Criterion(key, body["weight"], body["met"], body.get("card", ""))
                  for group in groups for key, body in shared.get(group, {}).items()]
        for entry in spec.get("task", []):
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
    head = (git(LAYOUT.root, "rev-parse", "--short", "HEAD") or "unknown").strip()
    dirty = git(LAYOUT.root, "status", "--porcelain")
    return f"{head}-dirty" if dirty and dirty.strip() else head


def run_dir(run: str) -> Path:
    """where one run's fixtures, outputs and sheet live.

    # Arguments

    * `run` - the run name

    # Returns

    `eval/results/<run>`
    """
    return HERE / "results" / run


def cmd_tasks() -> None:
    """print the task set with its point totals."""
    tasks = load_tasks()
    by_category: dict[str, list[Task]] = {}
    for task in tasks:
        by_category.setdefault(task.category, []).append(task)
    for category, group in by_category.items():
        print(f"\n{category}  ({len(group)} tasks)")
        for task in group:
            print(f"  {task.id:<26} {len(task.criteria):>2} criteria, {task.total():>2} pts   {task.title}")
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
    if root.exists():
        print(f"{TOOL}: {root} already exists; pick another run name", file=sys.stderr)
        sys.exit(Exit.USAGE)
    tasks = load_tasks()
    for task in tasks:
        for arm in ARMS:
            work = root / arm / task.id
            work.mkdir(parents=True)
            for name, body in task.fixture.items():
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                write_text(target, body.strip() + "\n")
            write_text(work / "TASK.md", f"# {task.title}\n\n{task.prompt}\n")
    meta = {"run": run, "brain": brain_version(), "tasks": [t.id for t in tasks], "arms": list(ARMS)}
    write_text(root / "run.json", json.dumps(meta, indent=1) + "\n")
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

    * `run` - the initialised run to pack
    """
    root = run_dir(run)
    if not (root / "run.json").is_file():
        print(f"{TOOL}: no run {run!r} - init it first", file=sys.stderr)
        sys.exit(Exit.USAGE)
    recall = LAYOUT.bin / "run" / "brain-recall.py"
    packed = 0
    for task in load_tasks():
        for arm in ARMS:
            work = root / arm / task.id
            lines = [f"# {task.title}", "", task.prompt, ""]
            if arm == "on":
                cards = run_recall(recall, task.prompt)
                lines += ["---", "", "## the rules that apply to this task", "",
                          "these came from the brain for this task. they are the standing rules",
                          "you work under - not part of the request.", "", cards, ""]
            lines += ["---", "",
                      "work in this directory. do not read or write outside it.",
                      "when you are done, report what is done and what is left."]
            write_text(work / "PROMPT.md", "\n".join(lines) + "\n")
            packed += 1
    print(f"{TOOL}: {packed} prompts -> {root}/<arm>/<task>/PROMPT.md")


def run_recall(recall: Path, prompt: str) -> str:
    """what the brain returns for one task prompt.

    # Arguments

    * `recall` - the brain-recall.py path
    * `prompt` - the task text to recall against

    # Returns

    recall's stdout, or a note when it could not run - never a silent empty
    string, which would make an `on` arm secretly an `off` arm
    """
    argv = [sys.executable, str(recall), " ".join(prompt.split())]
    try:
        done = subprocess.run(argv, capture_output=True, text=True, check=False,  # noqa: S603
                              timeout=60)
    except (OSError, subprocess.SubprocessError) as broken:
        return f"[brain-recall could not run: {broken}]"
    return done.stdout.strip() or "[brain-recall returned nothing for this task]"


def cmd_collect(run: str, reports: Path) -> None:
    """fold the agents' final reports into the run, for grading.

    several criteria judge what the agent SAID, not what it wrote - whether it
    reported state or narrated a changelog, whether it asked or assumed. those
    are ungradeable from the working directory alone

    # Arguments

    * `run` - the run to collect into
    * `reports` - a json file of {"<arm>/<task id>": "<final report>"}
    """
    root = run_dir(run)
    payload = json.loads(read_text(reports))
    for key, text in payload.items():
        arm, _, task_id = key.partition("/")
        target = root / arm / task_id / "REPORT.md"
        if target.parent.is_dir():
            write_text(target, text.rstrip() + "\n")
    print(f"{TOOL}: {len(payload)} reports collected into {root}")


def cmd_sheet(run: str) -> None:
    """write the grading sheet for a run.

    # Arguments

    * `run` - the run to build a sheet for
    """
    root = run_dir(run)
    if not (root / "run.json").is_file():
        print(f"{TOOL}: no run {run!r} - init it first", file=sys.stderr)
        sys.exit(Exit.USAGE)
    tasks = load_tasks()
    out = [f"# grading sheet - run `{run}`, brain `{json.loads(read_text(root / 'run.json'))['brain']}`\n",
           "tick a box when the criterion is MET. leave it unticked when it is not.\n",
           "grade one ARM at a time and do not look at the other while you do - the",
           "comparison is the measurement, so knowing which arm you are grading is",
           "the one thing that biases it.\n"]
    for arm in ARMS:
        out.append(f"\n---\n\n# ARM: {arm}\n")
        for task in tasks:
            out.append(f"\n## {task.id} - {task.title}\n")
            work = root / arm / task.id
            out.append(f"`{work}`\n")
            report = work / "REPORT.md"
            if report.is_file():
                said = read_text(report).strip()
                out.append(f"\n<details><summary>what it reported</summary>\n\n{said}\n\n</details>\n")
            if task.planted:
                out.append(f"\n> planted defect (grader only): {task.planted}\n")
            out.append("")
            out.extend(c.line() for c in task.criteria)
    write_text(root / "SHEET.md", "\n".join(out))
    print(f"{TOOL}: {root / 'SHEET.md'}")
    print(f"{TOOL}: {len(tasks) * len(ARMS)} task-arms, "
          f"{sum(len(t.criteria) for t in tasks) * len(ARMS)} judgements")


def parse_sheet(path: Path) -> dict[tuple[str, str], set[str]]:
    """the ticked criteria, keyed by (arm, task).

    # Arguments

    * `path` - the graded SHEET.md

    # Returns

    a mapping from (arm, task id) to the set of MET criterion keys
    """
    met: dict[tuple[str, str], set[str]] = {}
    arm = ""
    task = ""
    for line in read_text(path).splitlines():
        if line.startswith("# ARM: "):
            arm = line.removeprefix("# ARM: ").strip()
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
    root = run_dir(run)
    sheet = root / "SHEET.md"
    if not sheet.is_file():
        print(f"{TOOL}: no sheet for {run!r}", file=sys.stderr)
        sys.exit(Exit.USAGE)
    met = parse_sheet(sheet)
    tasks = {t.id: t for t in load_tasks()}
    scored: dict[str, dict[str, float]] = {arm: {} for arm in ARMS}
    for (arm, task_id), keys in met.items():
        task = tasks.get(task_id)
        if task is None or arm not in scored:
            continue
        earned = sum(c.weight for c in task.criteria if c.key in keys)
        scored[arm][task_id] = earned / task.total() if task.total() else 0.0
    meta = json.loads(read_text(root / "run.json"))
    meta["scores"] = scored
    write_text(root / "run.json", json.dumps(meta, indent=1) + "\n")
    for arm in ARMS:
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
    print(f"{'run':<14}{'brain':<14}{'n':>4}{'on':>8}{'off':>8}{'paired d':>10}{'wins':>7}{'losses':>8}")
    print("-" * 73)
    for run in runs:
        meta_path = run_dir(run) / "run.json"
        if not meta_path.is_file():
            print(f"{run:<14}(no run)")
            continue
        meta = json.loads(read_text(meta_path))
        scored = meta.get("scores", {})
        paired = [(scored.get("on", {}).get(tid), scored.get("off", {}).get(tid))
                  for tid in tasks if tid in scored.get("on", {}) and tid in scored.get("off", {})]
        if not paired:
            print(f"{run:<14}{meta.get('brain', '?'):<14}(not scored)")
            continue
        deltas = [on - off for on, off in paired]
        wins = sum(1 for d in deltas if d > 0)
        losses = sum(1 for d in deltas if d < 0)
        print(f"{run:<14}{meta.get('brain', '?'):<14}{len(paired):>4}"
              f"{statistics.mean(o for o, _ in paired):>8.3f}"
              f"{statistics.mean(f for _, f in paired):>8.3f}"
              f"{statistics.mean(deltas):>+10.3f}{wins:>7}{losses:>8}")
        if len(deltas) > 1:
            spread = statistics.stdev(deltas) / (len(deltas) ** 0.5)
            print(f"{'':<28}standard error {spread:.3f} - a difference under "
                  f"{2 * spread:.3f} is not distinguishable from noise at this n")
    print("\npaired d is the mean of (on - off) per task, not the difference of two means.")
    print("25 tasks resolves a graded effect; it does NOT resolve a small binary one.")


def cmd_clean(run: str) -> None:
    """delete a run's tree.

    # Arguments

    * `run` - the run to remove
    """
    root = run_dir(run)
    if root.exists():
        shutil.rmtree(root)
        print(f"{TOOL}: removed {root}")


def main() -> None:
    """dispatch the requested subcommand."""
    args = Args.from_argv()
    args.gate(TOOL, __doc__, Flag.CHECK)
    rest = args.positional()
    if not rest:
        print((__doc__ or "").strip())
        sys.exit(Exit.USAGE)
    command, names = rest[0], rest[1:]
    if command == "tasks":
        cmd_tasks()
    elif command in {"init", "pack", "sheet", "score", "clean"} and names:
        {"init": cmd_init, "pack": cmd_pack, "sheet": cmd_sheet,
         "score": cmd_score, "clean": cmd_clean}[command](names[0])
    elif command == "collect" and len(names) == COLLECT_ARGS:
        cmd_collect(names[0], Path(names[1]))
    elif command == "report" and names:
        cmd_report(names)
    else:
        print(f"{TOOL}: unknown or incomplete command {command!r}; `--help` lists what it accepts",
              file=sys.stderr)
        sys.exit(Exit.USAGE)


if __name__ == "__main__":
    main()
