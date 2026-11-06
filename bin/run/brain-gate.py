#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""b-gate: decide WHEN the review gate runs, how big it is, and when it stops.

a fixed lens set after every phase, looped until a pass comes back clean, would
review a 3-line phase like a 2k-line one and patch a design that keeps
producing findings round after round. this tool makes the three calls
deterministic, from the diff and the round counts, never from the agent's
mood (P30):

    b-gate phase [-s REV] [-t S|M|L] [-l]
        score the phase just built and add it to the pending total. prints
        `gate N` (run the review gate now, N reviewers) or `defer` (take the next
        phase; a later gate covers this one). --last gates any nonzero pending score
    b-gate round VALID SERIOUS
        record one adjudicated round: VALID findings, SERIOUS of them medium or
        worse. prints the ADJUDICATE event: all_invalid | valid_remain |
        final_fix | not_converging | capped
    b-gate design
        mark that DESIGN ran; the next round is its acceptance test (net decrease)
    b-gate reset
        delete this repo's gate state (CLEANUP runs it; the run leaves no residue)

the score: changed lines in code at 1, plus a structural weight per added,
deleted or renamed file. prose (shape.toml's `[scan] prose`) scores nothing: a
doc never buys the cold review, it gets the style gate. the plan's S/M/L tag is
the expected size; the measured diff overrides it when the phase is bigger

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
    UNTRACKED,
    Args,
    Change,
    DataLayout,
    Flag,
    Layout,
    LocalLayout,
    NoVerdict,
    RepoTree,
    ShapePolicy,
    Tool,
    UsageError,
)

# --------------------------------------------------
# external
# --------------------------------------------------
import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum

# --------------------------------------------------
# constants
# --------------------------------------------------
# the command this tool runs as, for its messages
TOOL = Layout.command(Path(__file__))
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
# prose suffixes score nothing; the list is shape.toml's, spelled once
PROSE = ShapePolicy.load(Layout.discover().shape_toml).prose
# structural weight per file event: a new or moved module reshapes the tree
ADDED_WEIGHT = 40.0
DELETED_WEIGHT = 20.0
RENAMED_WEIGHT = 40.0
BINARY_WEIGHT = 10.0
# each git status's weight; an untracked file is a new one
EVENT_WEIGHT = {"A": ADDED_WEIGHT, UNTRACKED: ADDED_WEIGHT, "D": DELETED_WEIGHT, "R": RENAMED_WEIGHT}


class Command(StrEnum):
    """b-gate's subcommands, as typed.

    # Example

        >>> [str(command) for command in Command]
        ['phase', 'round', 'design', 'reset']
    """

    PHASE = "phase"
    ROUND = "round"
    DESIGN = "design"
    RESET = "reset"


@dataclass
class GateState:
    """the pending work and round history for one repo checkout.

    lives in the private data dir's per-machine local/, never in the repo
    under review, so a finished run leaves nothing behind in the tree
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


def checkout() -> RepoTree:
    """the repo the cwd is in, alone: no superproject, no submodules.

    # Returns

    the one-repo tree

    # Raises

    NoVerdict outside a checkout
    """
    tree = RepoTree.containing(Path.cwd())
    if not tree.repos:
        raise NoVerdict(f"{Path.cwd()} is not inside a git checkout")
    return tree


def state_path(local: LocalLayout, top: Path) -> Path:
    """the gate-state file for one checkout.

    keyed by the checkout's top-level path, hashed, so a worktree and its main
    tree keep separate totals; the name prefix keeps it readable

    # Arguments

    * `local` - the data dir's per-machine layout; `writable()` when the state will be saved
    * `top` - the checkout's top-level path, `checkout().repos[0]`

    # Returns

    `<LocalLayout.gate>/<repo>-<hash8>.json`

    # Example

        >>> str(state_path(LocalLayout(Path("/d/local")), Path("/r/home")))
        '/d/local/gate/home-888329a7.json'
    """
    digest = hashlib.sha256(str(top).encode()).hexdigest()[:8]
    return local.gate / f"{top.name}-{digest}.json"


def score(change: Change) -> float:
    """one changed file's score: its changed lines, plus the weight of its file event.

    prose scores nothing - it gets the style gate. a file whose lines cannot be
    counted, binary or unreadable, scores BINARY_WEIGHT in their place

    # Arguments

    * `change` - the file, as `RepoTree.since` lists it

    # Returns

    the file's score

    # Example

        >>> changes = [Change(Path("/r/a.rs"), "M", (10, 2)), Change(Path("/r/b.rs"), "R", (0, 0)),
        ...            Change(Path("/r/logo.png"), "A", None), Change(Path("/r/docs/x.md"), "A", (8, 0))]
        >>> [score(change) for change in changes]
        [12.0, 40.0, 50.0, 0.0]
    """
    if change.path.suffix in PROSE:
        return 0.0
    lines = change.lines()
    return (BINARY_WEIGHT if lines is None else float(lines)) + EVENT_WEIGHT.get(change.status, 0.0)


def measure(since: str) -> float:
    """the score of everything the checkout changed since `since`, untracked files included.

    # Arguments

    * `since` - the base revision

    # Returns

    the summed score of every changed file

    # Raises

    RepoError when `since` does not resolve or git cannot list the checkout
    """
    return sum(map(score, checkout().since(since)), 0.0)


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


def main(args: Args) -> None:
    """dispatch the subcommand: `phase`, `round`, `design` or `reset`.

    `phase` accumulates the pending score and prints `gate N` or `defer`; `round`
    records a review round and prints the event it implies; `design` marks that a
    redesign was tried; `reset` deletes the state file. the whole command line
    is checked before local/ is touched, and the state is persisted after every
    subcommand but `reset`

    # Arguments

    * `args` - the parsed command line; the first positional is the subcommand,
      the rest are its operands (`round VALID SERIOUS`), and `--tag`, `--since`
      and `--last` shape `phase`

    # Raises

    UsageError for an unknown subcommand, a `round` without two counts, or a
    `--tag` that is not one of the plan tags; EditCopyMissing when this machine
    has no edit copy; NoVerdict when its data submodule is not checked out
    """
    name, *rest = args.positional()
    # --------------------------------------------------
    # the command line, refused before anything is read or written
    # --------------------------------------------------
    try:
        command = Command(name)
    except ValueError:
        raise UsageError(f"unknown command {name!r}; one of {', '.join(Command)}") from None
    tag = args.value(Flag.TAG).upper()
    if command is Command.PHASE and tag and tag not in TAG_SCORE:
        raise UsageError(f"{Flag.TAG.spelling} is one of {', '.join(TAG_SCORE)}")
    if command is Command.ROUND and not (len(rest) == ROUND_ARGS and all(n.isdigit() for n in rest)):
        raise UsageError(f"{command} takes VALID SERIOUS, two counts")
    # --------------------------------------------------
    # the checkout first, so a run outside one writes nothing; every command but reset saves the state,
    # so only reset leaves local/ as it is
    # --------------------------------------------------
    top = checkout().repos[0]
    local = DataLayout.discover().local
    path = state_path(local if command is Command.RESET else local.writable(), top)
    state = GateState.load(path)
    match command:
        # --------------------------------------------------
        # phase: accumulate, then gate or defer
        # --------------------------------------------------
        case Command.PHASE:
            state.tagged += TAG_SCORE.get(tag, 0.0)
            measured = measure(args.value(Flag.SINCE, "HEAD"))
            pending = max(state.tagged, measured - state.gated_at)
            if pending >= THRESHOLD or (args.has(Flag.LAST) and pending > 0):
                print(f"gate {reviewers(pending)}  (pending score {pending:.0f})")
                state = GateState(gated_at=measured)
            else:
                print(f"defer  (pending score {pending:.0f} < {THRESHOLD:.0f})")
            state.save(path)
        # --------------------------------------------------
        # round: record, then name the event
        # --------------------------------------------------
        case Command.ROUND:
            state.rounds.append([int(rest[0]), int(rest[1])])
            print(round_event(state.rounds, design_tried=state.design_tried))
            state.save(path)
        # --------------------------------------------------
        # design: the next round is the acceptance test against the last count
        # --------------------------------------------------
        case Command.DESIGN:
            state.design_tried = True
            state.rounds = state.rounds[-1:]
            state.save(path)
            print("design marked; the next round must show a net decrease")
        # --------------------------------------------------
        # reset: leave nothing behind
        # --------------------------------------------------
        case Command.RESET:
            path.unlink(missing_ok=True)
            print(f"reset {path.name}")


if __name__ == "__main__":
    Tool.of(TOOL, __doc__, positionals=(1, 3)).run(main)
