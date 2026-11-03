# knowledge graph: export and neo4j

what `graph.json` is for, and why the graph is not neo4j. the graph's shape: see
`bin/brainlib/graph.py`; how recall ranks it: see `bin/brainlib/recall.py`.

## graph.json
`bin/store/brain-graph.py` writes the graph out as `brain/graph/graph.json`, gitignored - an export
for a reader outside the brain, never an input. no brain tool reads it, so nothing ranks a stale copy.

## neo4j - the decision
not warranted as a runtime. neo4j is a server, a port, a process to babysit - infra for a graph that
fits in a small json file, against [[../brain/principles/principle-14-minimal-surface]] and "dont pull
infra unless needed". neo4j would add a stateful mutable store, the opposite of a graph re-derived
from the principles on demand. `graph.json` is typed nodes and edges, portable to any graph tool.

## context-mode (optional semantic layer)
the principles are plain markdown. for fuzzy/semantic recall on top of the deterministic graph, index the
store once with context-mode and `ctx_search` over it. that path is non-deterministic by construction
(bm25 + fusion), so it stays a convenience, never the contract. the graph is the contract.
