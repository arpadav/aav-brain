# schema: decision trace

the brain's own reasoning history: `~/.local/share/aav-brain/trace/decisions.jsonl` (the private logs submodule, via find_data), one decision per line, append-only.
the point is the decided-AGAINST entries - when a later session disagrees with a past call, the trace
shows WHERE it was made (`affects`) so it can be reversed precisely. written + read by `bin/brain-trace.py`
(via the `Decision` dataclass in `bin/brainlib.py`); brain-meta-curate and brain-self-refine consume it.

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
  "reversible": true,
  "supersedes": ""                  // ts of a prior entry this call overturns ("" if none)
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

## invariants
- append-only in normal operation: never overwrite or delete a past line during work. a reversal is a
  NEW entry with `supersedes` pointing at the old `ts`; the old line stays as history.
- ts uniqueness was retrofitted once: pre-microsecond entries shared a second-resolution stamp, so
  they were uniquified in append-order (no decision content changed) to make `supersedes` keyable.
  that is a one-time integrity migration, not a license to edit decisions.
- every appended entry needs at least `--skill`, `--decision`, `--chosen`.

## read modes
- `brain-trace.py --against`        : entries that rejected an option (worth revisiting).
- `brain-trace.py --low-confidence` : entries marked low confidence.

## lifecycle
- brain-self-refine reads the trace each run: for every decided-against entry it asks whether the
  reject reasons still hold (reinforce vs revise vs ask), then logs its own calls back here.
- a card/flow/script edit that overturns a logged call appends a new entry with `--supersedes <ts>`.
