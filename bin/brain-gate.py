#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-gate: decide WHEN the review gate runs, how big it is, and when it stops.

the gate used to run after every phase with a fixed lens set, and loop until a
pass came back clean. a 3-line phase drew the same review as a 2k-line one, and
a design that kept producing findings was patched round after round (measured:
62 top-level dispatches, 154 subagent transcripts, one session). this tool makes
the three calls deterministic, from the diff and the round counts, never from
the agent's mood (P30):

    python3 brain-gate.py phase [--since REV] [--tag S|M|L] [--last]
        score the phase just built and add it to the pending total. prints
        `gate N` (run the review gate now, N reviewers) or `defer` (take the next
        phase; a later gate covers this one). --last gates any nonzero pending score
    python3 brain-gate.py round VALID SERIOUS
        record one adjudicated round: VALID findings, SERIOUS of them medium or
        worse. prints the ADJUDICATE event: all_invalid | valid_remain |
        final_fix | not_converging | capped
    python3 brain-gate.py design
        mark that DESIGN ran; the next round is its acceptance test (net decrease)
    python3 brain-gate.py reset
        delete this repo's gate state (CLEANUP runs it; the run leaves no residue)

the score: changed lines in code at 1, in docs at 0.25, plus a structural weight
per added, deleted or renamed file. the plan's S/M/L tag is the expected size;
the measured diff overrides it when the phase is bigger than tagged

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, Exit, Flag, find_gate_state

# --------------------------------------------------
# external
# --------------------------------------------------
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem
# pending score at which the gate fires. about 300 changed code lines, or a
# handful of new modules - one reviewable sitting
THRESHOLD = 300.0
# reviewer count is 2 at the threshold and gains one per this much more score
REVIEWER_STEP = 400.0
MIN_REVIEWERS = 2
MAX_REVIEWERS = 6
# `round VALID SERIOUS`
ROUND_ARGS = 2
# round 1 with this many medium-or-worse findings is a design verdict, not a queue
SERIOUS_LIMIT = 5
# the plan's expected size per tag
TAG_SCORE = {"S": 50.0, "M": 200.0, "L": 600.0}
# per-line weight of a doc file; prose is cheap to review
DOC_WEIGHT = 0.25
DOC_SUFFIXES = frozenset({".md", ".rst", ".txt", ".adoc"})
# structural weight per file event: a new or moved module reshapes the tree
ADDED_WEIGHT = 40.0
DELETED_WEIGHT = 20.0
RENAMED_WEIGHT = 40.0
BINARY_WEIGHT = 10.0


@dataclass
class GateState:
    """the pending work and round history for one repo checkout.

    lives in the private data dir, never in the repo, so a finished run leaves
    nothing behind in the tree
    """

    # sum of plan tags since the last gate
    tagged: float = 0.0
    # measured diff score at the last gate; pending is measured minus this
    gated_at: float = 0.0
    # (valid, serious) per review round of the current gate
    rounds: list[list[int]] = field(default_factory=list)
    # DESIGN ran for the current gate; one more non-decrease is final
    design_tried: bool = False

    @classmethod
    def load(cls, path: Path) -> "GateState":
        """the stored state, or a fresh one.

        # Arguments

        * `path` - the state file

        # Returns

        the GateState read from `path`, or the default when it does not exist
        """
        if not path.exists():
            return cls()
        return cls(**json.loads(path.read_text()))

    def save(self, path: Path) -> None:
        """write the state, creating its directory.

        # Arguments

        * `path` - the state file
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self)) + "\n")


def state_path() -> Path:
    """the gate-state file for the current checkout.

    keyed by the checkout's top-level path, hashed, so a worktree and its main
    tree keep separate totals; the name prefix keeps it readable

    # Returns

    `<find_gate_state()>/<repo>-<hash8>.json`
    """
    top = git("rev-parse", "--show-toplevel").strip()
    digest = hashlib.sha256(top.encode()).hexdigest()[:8]
    return find_gate_state() / f"{Path(top).name}-{digest}.json"


def git(*argv: str) -> str:
    """run git and return stdout; fail loud on error.

    # Arguments

    * `argv` - the git arguments

    # Returns

    git's stdout
    """
    done = subprocess.run(["git", *argv], capture_output=True, text=True, check=False)  # noqa: S603, S607
    if done.returncode != 0:
        print(f"{TOOL}: git {' '.join(argv)}: {done.stderr.strip()}", file=sys.stderr)
        sys.exit(Exit.USAGE)
    return done.stdout


def line_weight(path: str) -> float:
    """the score of one changed line in this file.

    # Arguments

    * `path` - the file path

    # Returns

    DOC_WEIGHT for a doc file, 1.0 otherwise

    # Example

        >>> line_weight("book/intro.md"), line_weight("src/lib.rs")
        (0.25, 1.0)
    """
    return DOC_WEIGHT if Path(path).suffix in DOC_SUFFIXES else 1.0


def score_numstat(numstat: str) -> float:
    r"""the line score of `git diff --numstat` output.

    # Arguments

    * `numstat` - the numstat text: `added<TAB>deleted<TAB>path` per line

    # Returns

    weighted changed lines; a binary file (`-` counts) scores BINARY_WEIGHT

    # Example

        >>> score_numstat("10\t2\tsrc/a.rs\n8\t0\tREADME.md\n-\t-\tlogo.png\n")
        24.0
    """
    total = 0.0
    for row in numstat.splitlines():
        added, deleted, path = row.split("\t", 2)
        if added == "-":
            total += BINARY_WEIGHT
            continue
        total += (int(added) + int(deleted)) * line_weight(path)
    return total


def score_status(name_status: str) -> float:
    r"""the structural score of `git diff --name-status --find-renames` output.

    # Arguments

    * `name_status` - the name-status text: `<letter>[score]<TAB>path...` per line

    # Returns

    the added, deleted and renamed file weights summed

    # Example

        >>> score_status("A\tsrc/new.rs\nM\tsrc/a.rs\nR094\tsrc/b.rs\tsrc/c.rs\n")
        80.0
    """
    weights = {"A": ADDED_WEIGHT, "D": DELETED_WEIGHT, "R": RENAMED_WEIGHT}
    return sum(weights.get(row[:1], 0.0) for row in name_status.splitlines() if row)


def measure(since: str) -> float:
    """the score of everything changed since `since`, untracked files included.

    # Arguments

    * `since` - the base revision

    # Returns

    the line score plus the structural score of the working tree against `since`
    """
    # --------------------------------------------------
    # tracked: lines, then file events
    # --------------------------------------------------
    total = score_numstat(git("diff", "--numstat", "--find-renames", since))
    total += score_status(git("diff", "--name-status", "--find-renames", since))
    # --------------------------------------------------
    # untracked: each is a new file of its full length
    # --------------------------------------------------
    for path in git("ls-files", "--others", "--exclude-standard").splitlines():
        try:
            lines = len(Path(path).read_text().splitlines())
        except (UnicodeDecodeError, OSError):
            total += BINARY_WEIGHT + ADDED_WEIGHT
            continue
        total += lines * line_weight(path) + ADDED_WEIGHT
    return total


def reviewers(pending: float) -> int:
    """the reviewer count for a gate over this much pending score.

    # Arguments

    * `pending` - the score the gate covers

    # Returns

    MIN_REVIEWERS at the threshold, one more per REVIEWER_STEP, capped at MAX_REVIEWERS

    # Example

        >>> reviewers(120.0), reviewers(900.0), reviewers(9000.0)
        (2, 4, 6)
    """
    return max(MIN_REVIEWERS, min(MAX_REVIEWERS, MIN_REVIEWERS + int(pending // REVIEWER_STEP)))


def round_event(rounds: list[list[int]], *, design_tried: bool) -> str:
    """the ADJUDICATE event for the latest round.

    the hard limit is two rounds per gate. round 1 fixes and re-reviews; round 2
    either shows a decrease (fix it and move on, no third review) or does not
    (the design is the defect). after DESIGN, its one re-review is the acceptance
    test: a net decrease passes, anything else stops and goes to him

    # Arguments

    * `rounds` - (valid, serious) per round, latest last
    * `design_tried` - DESIGN already ran for this gate

    # Returns

    all_invalid | valid_remain | final_fix | not_converging | capped

    # Example

        >>> round_event([[0, 0]], design_tried=False), round_event([[9, 6]], design_tried=False)
        ('all_invalid', 'not_converging')
        >>> round_event([[6, 2], [2, 0]], design_tried=False), round_event([[6, 2], [7, 3]], design_tried=False)
        ('final_fix', 'not_converging')
        >>> round_event([[7, 3], [8, 2]], design_tried=True)
        'capped'
    """
    valid, serious = rounds[-1]
    if valid == 0:
        return "all_invalid"
    if len(rounds) == 1:
        return "not_converging" if serious >= SERIOUS_LIMIT else "valid_remain"
    if valid < rounds[-2][0]:
        return "final_fix"
    return "capped" if design_tried else "not_converging"


def main() -> None:
    """dispatch the subcommand."""
    args = Args.from_argv()
    args.gate(TOOL, __doc__, Flag.SINCE, Flag.TAG, Flag.LAST)
    command, *rest = args.positional() or ["--help"]
    path = state_path()
    state = GateState.load(path)
    # --------------------------------------------------
    # phase: accumulate, then gate or defer
    # --------------------------------------------------
    if command == "phase":
        tag = args.value(Flag.TAG).upper()
        if tag and tag not in TAG_SCORE:
            print(f"{TOOL}: --tag is one of {', '.join(TAG_SCORE)}", file=sys.stderr)
            sys.exit(Exit.USAGE)
        state.tagged += TAG_SCORE.get(tag, 0.0)
        measured = measure(args.value(Flag.SINCE, "HEAD"))
        pending = max(state.tagged, measured - state.gated_at)
        if pending >= THRESHOLD or (args.has(Flag.LAST) and pending > 0):
            print(f"gate {reviewers(pending)}  (pending score {pending:.0f})")
            state = GateState(gated_at=measured)
        else:
            print(f"defer  (pending score {pending:.0f} < {THRESHOLD:.0f})")
        state.save(path)
        return
    # --------------------------------------------------
    # round: record, then name the event
    # --------------------------------------------------
    if command == "round" and len(rest) == ROUND_ARGS and all(n.isdigit() for n in rest):
        state.rounds.append([int(rest[0]), int(rest[1])])
        print(round_event(state.rounds, design_tried=state.design_tried))
        state.save(path)
        return
    # --------------------------------------------------
    # design: the next round is the acceptance test against the last count
    # --------------------------------------------------
    if command == "design":
        state.design_tried = True
        state.rounds = state.rounds[-1:]
        state.save(path)
        print("design marked; the next round must show a net decrease")
        return
    # --------------------------------------------------
    # reset: leave nothing behind
    # --------------------------------------------------
    if command == "reset":
        path.unlink(missing_ok=True)
        print(f"reset {path.name}")
        return
    print(f"{TOOL}: unknown command; `--help` lists them", file=sys.stderr)
    sys.exit(Exit.USAGE)


if __name__ == "__main__":
    main()
