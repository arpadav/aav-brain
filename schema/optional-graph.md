# the knowledge graph

the brain ships a real, deterministic knowledge graph - not a grep, not a handwave. this documents
how it works and where neo4j fits (it is an optional export, never a runtime dependency).

## what it is
`bin/brain-graph.py` parses every card and emits, into `brain/graph/`:
- `graph.json` : the canonical artifact. nodes = principle + interest cards; edges = derived
  relationships. committed to the repo. byte-identical on re-run given the same cards.
- `graph.cypher` : a deterministic neo4j CREATE script. load it for a visual, ignore it otherwise.

`bin/brain-recall.py` reads `graph.json` and never re-walks the cards - the graph is the index.

## nodes
| kind | source | fields |
|---|---|---|
| principle | brain/principles/*.md | id, kind, headline(=rule), interest[], confidence, tells[], body_links[], path |
| interest | brain/intents/*.md | id, kind, headline(=one_line), path |

voice docs are retrieved by name, not traversal, so they are not nodes (minimal surface, P14).

## edges (all derived, never authored)
| type | rule | direction |
|---|---|---|
| serves | principle frontmatter `interest: [...]` | principle -> interest |
| served_by | the inverse of serves | interest -> principle |
| relates | principle body `[[principle-*]]` link | principle -> principle |
| tension | card frontmatter `tension: [...]`, symmetric | both directions |

**single source of truth:** each principle declares its interests once (`interest:`); served_by is
derived. there is no served_by frontmatter to drift. the builder also flags dangling references (a
serve to an unknown interest) and orphan nodes as `warnings` - the graph audits itself.

## determinism (so it can be committed and checked)
1. cards enumerated via sorted glob, never fs order.
2. nodes sorted by (kind, id); edges sorted by (type, src, dst); warnings sorted.
3. fixed field order per node; `json.dumps(indent=2, ensure_ascii=False)`; trailing newline; no
   timestamps or host paths beyond the repo-relative `path`.
4. `graph.cypher` emitted in the same stable order, so it is byte-identical too.

`python3 bin/brain-graph.py --check` rebuilds in memory and exits 1 if it differs from the committed
`graph.json`. wire it into a pre-commit hook so the graph can never silently drift from the cards.

## query (deterministic)
`brain-recall.py "<task>"`:
1. tokenize the task (lower, drop <3 chars + stopwords).
2. seed: score each node = 3*(hits in tells+headline) + 1*(hits in id). keep score>0.
3. traverse one hop: each seed spreads `0.5 * its score` along serves/served_by/relates.
4. rank by (-score, kind_rank, id) - a total order, identical every run.
5. emit top-n with the rule, the path, and the edge each card was reached by.

same task -> same ranked cards. no embeddings, no server, offline.

## neo4j - the decision
not warranted as a runtime. the corpus is ~30 cards; neo4j is a server, a port, a process to babysit
- infra for a graph that fits in a small json file, against [[../brain/principles/principle-14-minimal-surface]]
and "dont pull infra unless needed". a committed `graph.json` re-derived byte-identically IS the
deterministic graph. neo4j would add a stateful mutable store on top, the opposite of deterministic.

the request is honored by export, not daemon: `graph.cypher` loads the same graph into neo4j if you
want the visual (`cypher-shell < brain/graph/graph.cypher`). real knowledge graph, typed nodes and
edges, portable to any graph tool - it just does not RUN on neo4j.

## context-mode (optional semantic layer)
the cards are plain markdown. for fuzzy/semantic recall on top of the deterministic graph, index the
store once with context-mode and `ctx_search` over it. that path is non-deterministic by construction
(bm25 + fusion), so it stays a convenience, never the contract. the graph is the contract.
