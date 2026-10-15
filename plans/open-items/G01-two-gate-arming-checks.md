# G01: two tools decide whether a phase buys the review gate
The issue is with gate arming after the computer-1/computer-2 merge (e.g. a 120-line phase: `brain-gate.py phase` and `brain-shape.py --since` can both rule on it).

## What
- `brain-gate.py phase` (from computer-1) is AUTHORITATIVE. It scores the phase (code lines at 1, doc lines at 0.25, plus a weight per added/deleted/renamed file), carries the pending score across phases, fires at 300, sizes the gate at 2-6 reviewers, and caps it at two rounds.
- `brain-shape.py --since` (from computer-2) is SECONDARY. It arms the gate when a phase's churn crosses `[budget]` in `shape.toml` (4 files or 400 lines, prose excluded). Its only remaining exit is `under_budget` (IMPL -> VERIFY), taken when `brain-gate.py` says `defer` on the final phase.
- The IMPL doc in `brain/flow/flow.toml` says: where the two disagree, `brain-gate.py` wins, and the disagreement is noted here.

## Issue
Both tools measure the same diff with different weights, so they can disagree. Keeping both was the merge decision (2026-10-15: "id like to keep both, but prioritize c1? and if c2 was redudant then it can be pruned/removed later"). No run has compared them yet.

## Decisions
**Recommended: A, after three real builds.** Prune only once real disagreements are on record.

| | Option | Effect |
|---|---|---|
| A | Prune `[budget]` and `under_budget` | One tool decides. `brain-shape.py` keeps its structure scan (file length, fan-out, duplicate types) for the PHASEGATE structure lens. |
| B | Keep both | The secondary signal stays. Every disagreement is logged below. |
| C | Fold `[budget]` into `brain-gate.py` | `brain-gate.py` reads its threshold and prose exclusion from `shape.toml`. One policy file, one decider. |

Does `brain-shape.py --since` ever arm a gate that `brain-gate.py` deferred, on a phase where the review then found something real?

## Disagreements
- (none recorded yet)

## Your call

<!-- sha256: 1c1fe8ecf08f46a245a11f5dd8fa82506fe98870c70807f32b2ec9d7e03dc3ee -->
