# the execution flow

the brain follows a deterministic execution flow when it runs a task. it is a first-class artifact,
co-equal with the knowledge graph (schema/optional-graph.md) and kept strictly separate from it (P30):
the graph is CONTEXT ("which principles apply"), the flow is SEQUENCE ("what step is next").

## what it is
- `brain/flow/flow.toml` : the authored SOURCE - entries + states + transitions, hand-edited. the
  flow's data, the way the markdown cards are the graph's data. there is no built copy.
- `bin/run/brain-walk.py` reads flow.toml directly and steps it; `bin/store/brain-flow.py` renders the doc
  view. both load and validate it through `brainlib.Flow` - one parse, one set of checks (P31).

## entries
an `[[entries]]` table names one way into the flow:

| field | meaning |
|---|---|
| skill | the entry skill he types (never given a load directive: it is the caller) |
| state | the state it seeds the walk at |
| mode | the mode it walks in; `brain-walk.py --mode <mode>` must name one of these |

## states
a `[[states]]` table in flow.toml:

| field | meaning |
|---|---|
| id | unique state name |
| kind | entry / work / gate / boundary / halt / terminal |
| owner | the brain skill or cold agent that runs the state |
| recall | true => the one coupling to the graph: brain-walk fires brain-recall before the owner runs |
| terminal | true => an end state with no exit (DONE, BLOCKED) |
| doc | one-line description |

## transitions
a `[[transitions]]` table:

| field | meaning |
|---|---|
| src | the state this leaves |
| on | the outcome EVENT the owner returns |
| dst | the next state |
| guard | optional mode: `name` admits only that entry mode, `!name` every other, empty all |
| boundary | true => the single sanction transition that flips ask-first -> execute-through |

`(src, on, mode)` resolves to at most one edge, so `step()` is a pure deterministic function.

## validation (brain-walk refuses to step, brain-flow refuses to render, an unsound flow)
- no dangling endpoints (every src/dst/entry state is a real state).
- every guard names a declared entry mode.
- exactly one `boundary` transition.
- no `(src, on)` resolving to two edges in any mode - the step must be unambiguous.
- every non-terminal state has an outgoing transition.
- every state is reachable from an entry (forward).
- every state can reach a terminal (reverse - no sink-trap).
- every owner resolves to a skill, agent or script.

## flow <-> graph (one-directional)
a state may CALL the graph (its `recall` flag -> brain-recall loads the relevant cards). the graph
NEVER calls the flow. which card ranks #1 cannot change a transition; transitions depend only on
(state, event). knowledge never steers sequence. that asymmetry is the separation.

## the doc view
`docs/DEV_FLOWCHART.md` is POPULATED by `brain-flow.py` from the tracked template
`docs/templates/DEV_FLOWCHART.md` (prose, with `<!-- fill: ... -->` markers) and flow.toml (the diagram
and the state table). re-run it after editing either; `brain-flow.py --check` fails while the doc is stale.
