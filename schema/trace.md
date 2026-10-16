# schema: decision trace

the brain's own reasoning history: `~/.local/share/aav-brain/trace/decisions.jsonl` (the private logs submodule, via find_data), one decision per line, append-only.
the point is the decided-AGAINST entries - when a later session disagrees with a past call, the trace
shows WHERE it was made (`affects`) so it can be reversed precisely. written + read by `bin/store/brain-trace.py`
(via the `Decision` dataclass in `bin/brainlib/store.py`); brain-meta-curate and brain-self-refine consume it.

## one entry (json object per line)
```json
{
  "ts": "2026-06-13T18:53:55.123456Z", // iso utc microsecond, stamped at append; unique key (envelope)
  "session": "<harness session id>", // derived from the harness session var or --session (envelope)
  "skill": "brain-self-refine",    // which skill made the call
  "decision": "<the question faced>",
  "chosen": "<what won>",
  "against": [                       // the rejected options + why (the point of the log)
    {"option": "<name>", "why": "<reason it lost>"}
  ],
  "affects": "<path the call lives at>",   // where a reversal would edit
  "principle": ["P29", "P32"],             // the cards that governed the call
  "confidence": "high",            // high | medium | low
  "supersedes": "",                 // ts of a prior entry this call overturns ("" if none)
  "repo": "brain",                  // NAME of the git repo affects is relative to (envelope)
  "stale": true,                    // MARK, present only when pruned; readers skip it
  "pinned": true                    // MARK, present only when restored; prunes refuse it
}
```

## fields
- `ts`, `session` : envelope, set at append. `ts` is stamped now if not passed; `session` is the
  harness's own session id (e.g. `$CLAUDE_CODE_SESSION_ID`) so the decisions of one run group
  together - derived from an existing var, never a custom one; `--session` overrides.
- `decision` / `chosen` : the fork and the winner, in prose.
- `against` : list of `{option, why}`; populated from each `--reject opt=why`. an entry with a
  non-empty `against` is what `--against` surfaces for revisiting.
- `affects` : the precise path (file, or a glob/dir when the call spans many); the reversal pointer.
- `principle` : the cards cited; one `--principle` each.
- `confidence` : `--low-confidence` surfaces the `low` ones.
- `supersedes` : the `ts` of the entry this one overturns (ts is microsecond-unique, so it names
  exactly one entry). a read (`--against`) marks the superseded entry `[SUPERSEDED]` so a settled
  reversal is not re-litigated as an open decision.
- `repo` : the NAME of the git repo `affects` is relative to, stamped at append. without it the same
  relative path names a live file in the repo the run happened in and nothing anywhere else, so a
  cross-repo entry is indistinguishable from a stale one. the name, never the path (P32). entries
  written before this field read as `unattributed`.
- `stale` / `pinned` : MARKS, not payload. they live in `Ledger.META`, so setting one does not change
  a record's content id and a re-merge still dedups it onto the same row. present only when set -
  clearing writes no `false`, so an unmarked record is byte-identical to one never marked.

## invariants
- append-only in normal operation: never overwrite or delete a past line during work. a reversal is a
  NEW entry with `supersedes` pointing at the old `ts`; the old line stays as history.
- forgetting is a MARK, never a delete. `--prune` sets `stale` and every reader but `--pruned` skips
  the line; the line itself stays. that is what makes it reversible: `--restore` clears the mark and
  sets `pinned`, and a later `--prune` refuses a pinned entry rather than re-taking it.
- ELIGIBLE IS NOT A VERDICT. `--stale-candidates` applies two mechanical filters - older than the
  window in `prune.toml`, and an `affects` that resolves to nothing - and produces a READING LIST.
  each one is then judged against what the brain is today. pruning the whole list would take out the
  oldest and most load-bearing decisions in the store first.
- ts uniqueness was retrofitted once: pre-microsecond entries shared a second-resolution stamp, so
  they were uniquified in append-order (no decision content changed) to make `supersedes` keyable.
  that is a one-time integrity migration, not a license to edit decisions.
- every appended entry needs at least `--skill`, `--decision`, `--chosen`.

## read modes
- `brain-trace.py --against`          : entries that rejected an option (worth revisiting).
- `brain-trace.py --low-confidence`   : entries marked low confidence.
- `brain-trace.py --stale-candidates` : entries old enough to be worth judging for pruning.
- `brain-trace.py --pruned`           : entries currently marked stale.

## mark modes (brain-self-refine only)
- `brain-trace.py --prune <ts>`   : mark stale. refused when the entry is pinned.
- `brain-trace.py --restore <ts>` : clear stale AND pin, so no later prune can take it again.

the eligibility window is authored in `prune.toml` and scales with this repo's commit rate: a repo
being reshaped weekly invalidates a three-week-old decision, a quiet one does not.

## lifecycle
- brain-self-refine reads the trace each run: for every decided-against entry it asks whether the
  reject reasons still hold (reinforce vs revise vs ask), then logs its own calls back here.
- a card/flow/script edit that overturns a logged call appends a new entry with `--supersedes <ts>`.
- brain-learner runs the reverse direction at DONE: if this run's signal shows a pruned topic is live
  again, it `--restore`s that entry, which also pins it against being pruned a second time.
