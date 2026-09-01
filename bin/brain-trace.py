#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""brain-trace: append to and read the brain's decision-trace log.

the trace (the private data dir's trace/decisions.jsonl, OUTSIDE the repo - see
brainlib.find_data) is append-only reasoning history. the
point is the decided-AGAINST entries: when a later session disagrees with a
past call, the trace shows WHERE it was made (the `affects` pointer) so it can
be reversed precisely. brain-meta-curate and brain-self-refine read it

an entry about an architecture the brain has since left is noise in every one
of those reads, so the trace can FORGET - but only by marking, never by
deleting. `--prune` sets `stale` and the readers skip it; `--restore` clears
the mark and sets `pinned`, which prunes refuse to touch. that is what makes
forgetting reversible: reintroducing an entry is clearing a flag, not
recovering a line from a backup that was never taken

    # append a decision (each --reject is option=why it was rejected). SINGLE-quote
    # every value: a decision text is data, not something for the shell to expand
    python3 brain-trace.py --skill brain-plan --decision '...' --chosen '...' \
        --reject 'three scripts=violates P19' --affects bin/brain-fmt.py --principle P19
    #   optional: --confidence high|medium|low   --supersedes TS   --session ID

    # read decisions worth revisiting (--against and --reject are kept distinct:
    # --reject WRITES a rejected option, --against READS entries that have one)
    python3 brain-trace.py --against            entries that rejected an option
    python3 brain-trace.py --low-confidence     entries marked low confidence

    # pruning: a mark, never a delete. only brain-self-refine prunes
    python3 brain-trace.py --stale-candidates      entries whose affects resolves to nothing
    python3 brain-trace.py --prune TS [--prune TS] mark stale; readers skip it
    python3 brain-trace.py --restore TS           unmark AND pin, so it cannot be pruned again
    python3 brain-trace.py --pruned               what is currently marked stale

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, DataLayout, Decision, Env, Exit, Flag, Layout, Ledger, PrunePolicy, find_repo

# --------------------------------------------------
# external
# --------------------------------------------------
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem

class Locality(StrEnum):
    """where an entry's `affects` pointer stands relative to this repo.

    an entry is written in whatever repo the run happened in, and `affects` is
    relative to that repo. so "the path is not on disk" means one thing for an
    entry from here and something else entirely for one from elsewhere - the
    distinction the eligibility list has to show rather than flatten
    """

    LIVE = "live"
    GONE = "gone"
    ELSEWHERE = "elsewhere"
    NO_POINTER = "no pointer"


@dataclass(frozen=True)
class Trace:
    """the decision trace, and every operation the tool performs on it.

    the modes share the ledger, the superseded set and the mark vocabulary, so
    they are methods on the corpus rather than a flat module of functions that
    each re-open it (P26)

    # Example

        Trace.discover().candidates()
    """

    ledger: Ledger

    @classmethod
    def discover(cls) -> "Trace":
        """the trace at its discovered path.

        the prune policy is NOT loaded here: every logged decision goes through
        this constructor, and a malformed `prune.toml` must not be able to stop
        the brain recording one. `candidates` loads it, which is the only mode
        that reads it

        # Returns

        a Trace over the ledger at `DataLayout.discover().decisions`
        """
        return cls(Ledger(DataLayout.discover().decisions))
    @staticmethod
    def locality(row: dict[str, Any], here: str, root: Path) -> Locality:
        """where this entry's `affects` stands, judged from `here`.

        an entry recorded in another repo is ELSEWHERE: its relative path names
        a file that repo has and this one does not, and calling that "gone" is
        what would put a live, load-bearing decision on a prune list. running
        outside any repo makes every relative path equally meaningless, so the
        whole trace reads ELSEWHERE rather than resolving against a stray cwd

        # Arguments

        * `row` - one trace record
        * `here` - the name of the repo this process is running in, or `""`
        * `root` - that repo's root; `affects` is relative to it, never to cwd

        # Returns

        LIVE when every path exists, GONE when one does not and the entry is
        attributable here, ELSEWHERE when it cannot be judged from this repo,
        NO_POINTER when it names no path at all

        # Example

            >>> Trace.locality({"affects": "", "repo": "brain"}, "brain", Path())
            <Locality.NO_POINTER: 'no pointer'>
            >>> Trace.locality({"affects": "x", "repo": "other"}, "brain", Path())
            <Locality.ELSEWHERE: 'elsewhere'>
            >>> Trace.locality({"affects": "x", "repo": "brain"}, "", Path())
            <Locality.ELSEWHERE: 'elsewhere'>
        """
        # --------------------------------------------------
        # a pointer-less entry is the HARDEST to reverse, so it is surfaced
        # rather than treated as resolved and exempted forever
        # --------------------------------------------------
        paths = [p.strip() for p in row.get("affects", "").split(",") if p.strip()]
        if not paths:
            return Locality.NO_POINTER
        # --------------------------------------------------
        # a relative path only means something in the repo it was written in
        # a legacy entry carries no repo and is judged here on best effort, which
        # is what `unattributed` in the listing warns the reader about
        # --------------------------------------------------
        origin = str(row.get("repo", ""))
        if not here or (origin and origin != here):
            return Locality.ELSEWHERE
        return Locality.LIVE if all((root / p).exists() for p in paths) else Locality.GONE
    def mark(self, args: Args) -> None:
        """set or clear the stale/pinned marks named on the command line.

        # Arguments

        * `args` - the parsed command line, carrying --prune / --restore timestamps
        """
        # --------------------------------------------------
        # refuse a malformed request BEFORE writing anything: a flag that lost
        # its value is a typo, and half-applying it is worse than refusing
        # --------------------------------------------------
        asked, restoring = args.values(Flag.PRUNE), args.values(Flag.RESTORE)
        if starved := args.starved(Flag.PRUNE, Flag.RESTORE):
            print(f"{TOOL}: {', '.join(starved)} given no timestamp", file=sys.stderr)
            sys.exit(Exit.USAGE)
        if not asked and not restoring:
            print(f"{TOOL}: no timestamp given; `--prune TS` and `--restore TS` each need one",
                  file=sys.stderr)
            sys.exit(Exit.USAGE)
        # --------------------------------------------------
        # a pin outranks a prune, so collect the pinned set first
        # --------------------------------------------------
        rows = self.ledger.read()
        pinned = {row["ts"] for row in rows if row.get("pinned")}
        present = {row.get("ts", "") for row in rows}
        # --------------------------------------------------
        # prune side: skip anything pinned, and name what was skipped
        # --------------------------------------------------
        refused = [ts for ts in asked if ts in pinned]
        stamps: dict[str, dict[str, bool]] = {ts: {"stale": True} for ts in asked if ts not in pinned}
        # --------------------------------------------------
        # restore side: clear the mark AND pin, unconditionally
        # --------------------------------------------------
        stamps |= {ts: {"stale": False, "pinned": True} for ts in restoring}
        # --------------------------------------------------
        # stamp, then account for every timestamp that landed nowhere
        # --------------------------------------------------
        touched = self.ledger.mark(stamps)
        for ts in refused:
            print(f"{TOOL}: {ts} is pinned, not pruned")
        for ts in sorted(set(stamps) - present):
            print(f"{TOOL}: {ts} matches no entry")
        print(f"{TOOL}: marked {touched} entr{'y' if touched == 1 else 'ies'}")

    def candidates(self) -> None:
        """print the entries OLD ENOUGH to be worth judging for pruning.

        this is a reading list, not a verdict. two mechanical filters run - the
        entry predates the policy window, and its pointer no longer stands - and
        everything past them is judged one at a time against what the brain is
        today. pruning the whole list would take out the oldest and most
        load-bearing decisions in the store, which are the ones a long-lived
        entry is most likely to be

        each entry is tagged with where its pointer stands: `gone` (written here,
        path no longer exists), `elsewhere` (written in another repo, so nothing
        can be concluded from here) or `no pointer` (names no path at all, which
        makes it the hardest of the three to reverse)
        """
        # --------------------------------------------------
        # the window follows how fast this repo is actually moving
        # --------------------------------------------------
        layout = Layout.discover()
        policy = PrunePolicy.load(layout.prune_toml)
        rate = policy.commit_rate(layout.root)
        cutoff = policy.cutoff(rate)
        # judged from the BRAIN, which is where the paths are resolved against,
        # so the answer does not change with the directory the tool is run from
        here = layout.root.name
        # --------------------------------------------------
        # candidates: unmarked, past the cutoff, pointer no longer standing
        # --------------------------------------------------
        rows = self.ledger.read()
        overturned = self.overturned(rows)
        judgeable = {Locality.GONE, Locality.NO_POINTER}
        eligible = [(row, self.locality(row, here, layout.root)) for row in rows
                    if not row.get("stale") and not row.get("pinned")
                    and row.get("ts", "") < cutoff]
        eligible = [(row, where) for row, where in eligible if where in judgeable]
        for row, where in eligible:
            # a legacy entry predates `repo`, so its path check is best effort
            note = where.value if row.get("repo") else f"{where.value}, unattributed"
            self.show(row, overturned, note=note)
        # --------------------------------------------------
        # summarise the window and what the list is NOT
        # --------------------------------------------------
        print(f"{TOOL}: {rate:.1f} commits/week -> {policy.window_days(rate)}-day window, "
              f"cutoff {cutoff}")
        print(f"{TOOL}: {len(eligible)} ELIGIBLE to be judged - NOT a prune list. read each one and "
              f"ask whether the brain still works this way; prune only the ones that do not")
    def overturned(self, rows: list[dict[str, Any]]) -> set[str]:
        """the timestamps a later entry supersedes.

        # Arguments

        * `rows` - the records to scan

        # Returns

        the superseded timestamps, which are no longer live decisions
        """
        return {row.get("supersedes", "") for row in rows if row.get("supersedes")}
    def show(self, row: dict[str, Any], overturned: set[str], note: str = "") -> None:
        """print one trace entry in the read-mode format.

        # Arguments

        * `row` - the record to print
        * `overturned` - the timestamps a later entry supersedes
        * `note` - an extra tag, e.g. where the entry's pointer stands
        """
        # --------------------------------------------------
        # the marks a reader needs, appended in a fixed order
        # --------------------------------------------------
        tags = f" [{note}]" if note else ""
        tags += " [SUPERSEDED]" if row.get("ts") in overturned else ""
        tags += " [STALE]" if row.get("stale") else ""
        tags += " [PINNED]" if row.get("pinned") else ""
        # --------------------------------------------------
        # header, then the call, then the rejected options if any
        # --------------------------------------------------
        print(f"{row.get('ts','')} [{row.get('skill','?')}] affects={row.get('affects','')}{tags}")
        print(f"  decided: {row.get('decision','')} -> {row.get('chosen','')}")
        if why := "; ".join(a.get("why", "") for a in row.get("against", [])):
            print(f"  against: {why}")
    def read(self, args: Args) -> None:
        """print the entries a later session should revisit, or the pruned ones.

        # Arguments

        * `args` - the parsed command line, selecting which read this is
        """
        # --------------------------------------------------
        # load the trace and the reversals it already settled
        # --------------------------------------------------
        rows = self.ledger.read()
        overturned = self.overturned(rows)
        # --------------------------------------------------
        # --pruned inverts the filter: it shows only what is marked
        # --------------------------------------------------
        only_pruned = args.has(Flag.PRUNED)
        for row in rows:
            # a pruned entry is invisible to every read but --pruned, which is
            # what makes the mark equivalent to a delete without being one
            if bool(row.get("stale")) != only_pruned:
                continue
            keep = only_pruned or (args.has(Flag.AGAINST) and row.get("against")) or (
                args.has(Flag.LOW_CONFIDENCE) and row.get("confidence") == "low")
            if keep:
                self.show(row, overturned)
    def append(self, args: Args) -> None:
        """log one decision to the trace.

        # Arguments

        * `args` - the parsed command line, carrying the decision's fields
        """
        # --------------------------------------------------
        # the three fields without which a record is unreadable later (P38)
        # --------------------------------------------------
        required = {flag: args.value(flag) for flag in (Flag.SKILL, Flag.DECISION, Flag.CHOSEN)}
        if missing := [flag for flag, value in required.items() if not value]:
            print(f"{TOOL}: no value for {', '.join(missing)}; `--help` lists what it accepts",
                  file=sys.stderr)
            sys.exit(Exit.USAGE)
        # --------------------------------------------------
        # each --reject is one option=why pair
        # --------------------------------------------------
        against: list[dict[str, str]] = [dict(zip(("option", "why"), pair.split("=", 1), strict=False))
                                         for pair in args.values(Flag.REJECT)]
        decision = Decision(
            skill=required[Flag.SKILL],
            decision=required[Flag.DECISION],
            chosen=required[Flag.CHOSEN],
            against=against,
            affects=args.value(Flag.AFFECTS),
            repo=find_repo(),
            principle=args.values(Flag.PRINCIPLE),
            confidence=args.value(Flag.CONFIDENCE, "medium"),
            supersedes=args.value(Flag.SUPERSEDES),
        )
        # --------------------------------------------------
        # session: the explicit flag wins, else the harness's own id (P17, P32)
        # --------------------------------------------------
        session = args.value(Flag.SESSION) or Env.SESSION_ID.read()
        written = decision.trace(self.ledger, session=session)
        print(f"{TOOL}: appended -> {written}")


# each mode is selected by its own flags; a token that merely SPELLS another
# mode's flag must not silently re-route the run, so mixing them is refused
MODES: tuple[tuple[str, tuple[Flag, ...]], ...] = (
    ("mark", (Flag.PRUNE, Flag.RESTORE)),
    ("candidates", (Flag.STALE_CANDIDATES,)),
    ("read", (Flag.AGAINST, Flag.LOW_CONFIDENCE, Flag.PRUNED)),
    ("append", (Flag.SKILL, Flag.DECISION, Flag.CHOSEN)),
)


def main() -> None:
    """dispatch the requested trace mode."""
    args = Args.from_argv()
    args.gate(TOOL, __doc__, Flag.SKILL, Flag.DECISION, Flag.CHOSEN, Flag.REJECT, Flag.AFFECTS,
              Flag.PRINCIPLE, Flag.CONFIDENCE, Flag.SUPERSEDES, Flag.SESSION, Flag.AGAINST,
              Flag.LOW_CONFIDENCE, Flag.STALE_CANDIDATES, Flag.PRUNE, Flag.RESTORE, Flag.PRUNED)
    # --------------------------------------------------
    # exactly one mode, or none (which is an append attempt)
    # --------------------------------------------------
    picked = [name for name, flags in MODES if any(args.has(flag) for flag in flags)]
    if len(picked) > 1:
        print(f"{TOOL}: {' and '.join(picked)} flags cannot be combined", file=sys.stderr)
        sys.exit(Exit.USAGE)
    # --------------------------------------------------
    # one trace, four modes
    # --------------------------------------------------
    trace = Trace.discover()
    mode = picked[0] if picked else "append"
    if mode == "mark":
        trace.mark(args)
    elif mode == "candidates":
        trace.candidates()
    elif mode == "read":
        trace.read(args)
    else:
        trace.append(args)


if __name__ == "__main__":
    main()
