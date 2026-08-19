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

    # append a decision (each --reject is option=why it was rejected)
    python3 brain-trace.py --skill brain-plan --decision "..." --chosen "..." \
        --reject "three scripts=violates P19" --affects bin/brain-fmt.py --principle P19

    # read decisions worth revisiting (--against and --reject are kept distinct:
    # --reject WRITES a rejected option, --against READS entries that have one)
    python3 brain-trace.py --against            entries that rejected an option
    python3 brain-trace.py --low-confidence     entries marked low confidence

Author: aav
"""
# --------------------------------------------------
# local
# --------------------------------------------------
from brainlib import Args, DataLayout, Decision, Env, Flag, Ledger, trace_decision

# --------------------------------------------------
# external
# --------------------------------------------------
import sys
from pathlib import Path

# --------------------------------------------------
# constants
# --------------------------------------------------
# this tool's own name, for its messages; derived so a rename cannot desync them
TOOL = Path(__file__).stem

def main() -> None:
    """append a decision, or read the trace for entries worth revisiting."""
    args = Args.from_argv()
    # --------------------------------------------------
    # read modes: surface decisions a later session should revisit
    # --------------------------------------------------
    if args.has(Flag.AGAINST) or args.has(Flag.LOW_CONFIDENCE):
        rows = Ledger(DataLayout.discover().decisions).read()
        # an entry whose ts a later entry supersedes is no longer live - mark it
        # so a re-litigated reversal is not re-read as an open decision
        overturned = {row.get("supersedes", "") for row in rows if row.get("supersedes")}
        for row in rows:
            keep = ((args.has(Flag.AGAINST) and row.get("against")) or
                    (args.has(Flag.LOW_CONFIDENCE) and row.get("confidence") == "low"))
            if keep:
                why = "; ".join(a.get("why", "") for a in row.get("against", []))
                tag = " [SUPERSEDED]" if row["ts"] in overturned else ""
                print(f"{row['ts']} [{row['skill']}] affects={row.get('affects','')}{tag}")
                print(f"  decided: {row['decision']} -> {row['chosen']}")
                if why:
                    print(f"  against: {why}")
        return
    # --------------------------------------------------
    # append mode: log one decision
    # --------------------------------------------------
    # a decision, a choice and an owning skill are what make a record readable
    # later; a flag that is present but carries no value is not an answer, so the
    # values are required rather than merely the flags (P38)
    required = {flag: args.value(flag) for flag in (Flag.SKILL, Flag.DECISION, Flag.CHOSEN)}
    if missing := [flag for flag, value in required.items() if not value]:
        sys.exit(f"{TOOL}: no value for {', '.join(missing)}\n"
                 "usage: brain-trace.py --skill S --decision D --chosen C [--reject opt=why ...] "
                 "[--affects PATH] [--principle P ...] [--supersedes TS] [--session ID] "
                 "| --against | --low-confidence")
    against: list[dict[str, str]] = [dict(zip(("option", "why"), pair.split("=", 1), strict=False))
                                     for pair in args.values(Flag.REJECT)]
    decision = Decision(
        skill=required[Flag.SKILL],
        decision=required[Flag.DECISION],
        chosen=required[Flag.CHOSEN],
        against=against,
        affects=args.value(Flag.AFFECTS),
        principle=args.values(Flag.PRINCIPLE),
        confidence=args.value(Flag.CONFIDENCE, "medium"),
        supersedes=args.value(Flag.SUPERSEDES),
    )
    # session: explicit flag wins, else derive from the harness's own session id
    # (no custom env var). only claude's is known here; another harness passes
    # --session or has its var added to this fallback when known (P17, P32)
    session = args.value(Flag.SESSION) or Env.SESSION_ID.read()
    written = trace_decision(decision, session=session)
    print(f"{TOOL}: appended -> {written}")


if __name__ == "__main__":
    main()
