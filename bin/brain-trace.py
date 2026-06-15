#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""brain-trace: append to and read the brain's decision-trace log.

the trace (the private data dir's trace/decisions.jsonl, OUTSIDE the repo - see
brainlib.find_data) is append-only reasoning history. the
point is the decided-AGAINST entries: when a later session disagrees with a
past call, the trace shows WHERE it was made (the `affects` pointer) so it can
be reversed precisely. brain-meta-curate and brain-self-refine read it.

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
# external
# --------------------------------------------------
import json
import os
import sys
from pathlib import Path

from brainlib import Decision, find_data, trace_decision

# --------------------------------------------------
# helpers (pure)
# --------------------------------------------------
def arg(args, name, default=""):
    """read the value after a flag, or a default.

    # Arguments
    * `args` - the argv list.
    * `name` - the flag to find.
    * `default` - returned when the flag is absent.

    # Returns
    the value following the flag, or the default.
    """
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default


def all_args(args, name):
    """every value following each occurrence of a repeated flag.

    # Arguments
    * `args` - the argv list.
    * `name` - the repeated flag.

    # Returns
    the list of values, one per occurrence.
    """
    return [args[i + 1] for i, a in enumerate(args) if a == name and i + 1 < len(args)]


# --------------------------------------------------
# entrypoint
# --------------------------------------------------
def main():
    """append a decision, or read the trace for entries worth revisiting."""
    args = sys.argv[1:]
    path = find_data() / "trace" / "decisions.jsonl"
    # --------------------------------------------------
    # read modes: surface decisions a later session should revisit
    # --------------------------------------------------
    if "--against" in args or "--low-confidence" in args:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
        # an entry whose ts a later entry supersedes is no longer live - mark it
        # so a re-litigated reversal is not re-read as an open decision.
        overturned = {row.get("supersedes", "") for row in rows if row.get("supersedes")}
        for row in rows:
            keep = (("--against" in args and row.get("against")) or
                    ("--low-confidence" in args and row.get("confidence") == "low"))
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
    if "--decision" not in args:
        sys.exit("usage: brain-trace.py --skill S --decision D --chosen C [--reject opt=why ...] "
                 "[--affects PATH] [--principle P ...] [--supersedes TS] [--session ID] "
                 "| --against | --low-confidence")
    against = [dict(zip(("option", "why"), pair.split("=", 1))) for pair in all_args(args, "--reject")]
    decision = Decision(
        skill=arg(args, "--skill", "unknown"),
        decision=arg(args, "--decision"),
        chosen=arg(args, "--chosen"),
        against=against,
        affects=arg(args, "--affects"),
        principle=all_args(args, "--principle"),
        confidence=arg(args, "--confidence", "medium"),
        supersedes=arg(args, "--supersedes"),
    )
    # session: explicit flag wins, else derive from the harness's own session id
    # (no custom env var). only claude's is known here; another harness passes
    # --session or has its var added to this fallback when known (P17, P32).
    session = arg(args, "--session") or os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    written = trace_decision(decision, session=session)
    print(f"brain-trace: appended -> {written}")


if __name__ == "__main__":
    main()
