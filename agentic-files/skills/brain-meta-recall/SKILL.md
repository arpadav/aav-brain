---
name: brain-meta-recall
description: "Retrieve the slice of Arpad's standards relevant to the task at hand - the queryable layer of his second brain. Load it before starting work, before reviewing, or whenever you need 'how would Arpad want this done' without dumping the whole store. It walks the deterministic knowledge graph: keyword-seeds the cards, traverses serves/served_by/relates edges one hop, returns the ranked principle + interest cards (with the edge each was reached by)."
---

# brain-recall: load the standards relevant to this task

the store is large; act with only the cards that matter for the task in front of you (context
hygiene, P12). this is the retrieval layer, and it is a real deterministic knowledge graph - same
task, same ranked cards, every time.

## setup (run first - discover the brain, no hardcoded path)
the brain scripts live in `$AAV_BRAIN/bin`, discovered via `brain-find` on PATH.
discover the store once:
```bash
eval "$(brain-find --export)"   # sets $AAV_BRAIN
```

## EXECUTE, do not hand-walk the graph
you MUST run `$AAV_BRAIN/bin/brain-recall.py` and use its ranked output. do NOT open `graph.json` and
traverse edges by hand - that re-derives the retrieval non-deterministically and defeats the point of
a committed graph. run the script; its stdout is authoritative.

## usage
given a task, run:

```bash
python3 $AAV_BRAIN/bin/brain-recall.py "<the task, in a few words>"
```

it keyword-seeds every card, traverses the graph one hop (serves / served_by / relates), ranks with
a fixed tie-break, and prints the top cards - each with its rule, its path, and the edge it was
reached by ("via serves from principle-03..."). then read the returned card files and cite them by
name.

other modes:
```bash
python3 $AAV_BRAIN/bin/brain-recall.py --tells unwrap_or     # which card a phrase belongs to
python3 $AAV_BRAIN/bin/brain-recall.py --neighbors P09        # one card and its edges (walk by hand)
python3 $AAV_BRAIN/bin/brain-recall.py --all                  # dump the index
python3 $AAV_BRAIN/bin/brain-recall.py -n 12 "<task>"         # top n (default 8)
```

## the graph
the graph is built deterministically from the cards by `$AAV_BRAIN/bin/brain-graph.py` into
`brain/graph/graph.json` (committed). nodes are principle + interest cards; edges are derived, never
authored (serves = principle->interest, served_by = the inverse, relates = body [[links]]). if you
add or edit a card, rebuild: `python3 $AAV_BRAIN/bin/brain-graph.py` (and `--check` fails if the committed
graph is stale). `graph.cypher` is an optional neo4j export for a visual; nothing depends on neo4j.

## what you get back
- principle cards (brain/principles/): the rule + why (the interest) + how to apply + tells + anti-pattern.
- interest cards (brain/intents/): the underlying need a cluster of rules serves (positions->interests).

## when to use
- before planning or implementing: recall the rules that govern this kind of work.
- before reviewing: recall the veto-level violations to check for.
- before writing a worker prompt: recall the constraints to bake in.

keep the recall tight - pull the handful of cards that apply, not the whole store.
