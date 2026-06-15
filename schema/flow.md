# the execution flow

the brain follows a deterministic execution flow when it runs a task. it is a first-class artifact,
co-equal with the knowledge graph (schema/optional-graph.md) and kept strictly separate from it (P30):
the graph is CONTEXT ("which principles apply"), the flow is SEQUENCE ("what step is next").

## what it is
- `brain/flow/flow.toml` : the authored SOURCE - states + transitions, hand-edited. the flow's data,
  the way the markdown cards are the graph's data.
- `brain/flow/flow.json` : the BUILT, validated, committed artifact. byte-identical on re-run.
- `bin/brain-flow.py` reads flow.toml, validates it, writes flow.json. `bin/brain-walk.py` steps
  flow.json. both share the State/Transition datatypes via brainlib (P31).

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
| guard | optional precondition (reserved; currently unused) |
| boundary | true => the single sanction transition that flips ask-first -> execute-through |

`(src, on)` is unique, so `step()` is a pure deterministic function.

## validation (brain-flow refuses to build an unsound flow)
- no dangling endpoints (every src/dst is a real state).
- exactly one `boundary` transition.
- no duplicate `(src, on)` - the step must be unambiguous.
- every non-terminal state has an outgoing transition.
- every state is reachable from IDEATION (forward).
- every state can reach a terminal (reverse - no sink-trap).
warnings fail the build; `--check` guards drift in CI, exactly like the graph.

## flow <-> graph (one-directional)
a state may CALL the graph (its `recall` flag -> brain-recall loads the relevant cards). the graph
NEVER calls the flow. which card ranks #1 cannot change a transition; transitions depend only on
(state, event). knowledge never steers sequence. that asymmetry is the separation.

## the doc view
`docs/DEV_FLOWCHART.md` is GENERATED from flow.json by `brain-flow.py --mermaid` - it cannot drift
from the artifact. regenerate it after editing flow.toml.
