# prior art: what i borrowed, and from whom

the brain isnt invented from scratch. it reuses known patterns for agent memory, self-supervision,
and queryable personal knowledge. what each one gave us:

## 1. principled negotiation -> the intent layer
fisher & ury, "getting to yes" (harvard negotiation project, 1981). core: focus on interests, not
positions. a position is a stated demand; an interest is the underlying need. BATNA is the walk-away
alternative that defines leverage.
taken: the whole INTENT_MAP. every position is decomposed into the interest it serves; the brain
serves interests, not literal commands. my BATNA (interrupt & do it myself) is the pressure the brain
relieves by serving the interest early.
- https://en.wikipedia.org/wiki/Getting_to_Yes
- https://en.wikipedia.org/wiki/Best_alternative_to_a_negotiated_agreement

## 2. memgpt / letta -> tiered, self-editing memory
memgpt (packer et al.) and its production successor letta: "llm as an operating system". two memory
tiers: in-context core (always loaded: rules + read/write blocks) and out-of-context external memory
(retrieved on demand). agents get memory-editing tools to update their own memory over time.
taken: the store is tiered. brain/CONSTITUTION.md is tier-1 core (always loaded); principles/ +
intents/ + voice/ are tier-2 retrieved corpus; evidence/ is tier-3 derived. the brain-meta-curate skill is
the memory-editing tool: it self-edits cards from new feedback. consent-is-explicit is our addition:
edit memory only from spoken signal, never from accepted diffs.
- https://www.letta.com/blog/agent-memory/
- https://docs.letta.com/guides/legacy/memgpt_agents_legacy

## 3. graphiti / zep -> the queryable temporal knowledge graph
zep, powered by graphiti: a bi-temporal knowledge graph for agent memory with hybrid retrieval
(semantic + bm25 + graph traversal, fused). reported context savings ~115k -> ~1.6k tokens on a
memory benchmark, p95 retrieval ~300ms.
taken: the retrieval model. brain-recall.py + brain-recall are a lightweight hybrid: keyword scoring +
weighted frontmatter (tells/interest) + the [[wikilink]] graph between cards. file-first (grep +
markdown, zero infra) so it runs today; a neo4j/graphiti upgrade is in ../schema/optional-graph.md
for when the corpus outgrows grep.
- https://arxiv.org/abs/2501.13956 (zep: a temporal knowledge graph architecture for agent memory)
- https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/

## 4. reflexion / planner-critic / llm-as-judge -> the self-supervision loop
known autonomous-agent patterns: reflexion (the agent critiques its own action and caches the
feedback), planner-critic / actor-critic (one agent proposes, another evaluates), llm-as-a-judge (an
llm scores outputs), recursive self-prompting (the agent prompts itself toward a goal).
taken: the DEV_FLOWCHART post-sanction loop is a planner-critic loop. brain-meta-author-prompt is the
actor, the brain-review-gate + brain-verifier agents are the cold critics, brain-execute is the
controller, brain-meta-curate is the reflexion cache. we use independent, cold, multi-lens critics
(matching my "cold/unguided, converge, single-nit" protocol) instead of a single self-critique,
because i distrust a single pass.
- https://en.wikipedia.org/wiki/LLM-as-a-Judge
- https://en.wikipedia.org/wiki/Automated_code_review

## 5. local-first markdown second brains -> the store format
basic-memory / obsidian-as-knowledge-graph + mcp servers. pattern: atomic markdown notes, one idea
per file, cross-linked with [[wikilinks]], traversable as a graph, local-first (data never leaves the
machine), readable/writable by the agent directly.
taken: the card format. each principle/interest is one atomic markdown file with frontmatter +
[[links]] (zettelkasten). the brain reads/writes them directly; nothing leaves my disk. the store is
diff-able and git-versioned, itself a record i control ([[../brain/principles/principle-09-git-sovereignty]]).

## 6. canonical-instruction files (CLAUDE.md / AGENTS.md / .cursorrules) -> the constitution
the 2026 convergence: a single canonical markdown file of standing instructions every agent reads
(CLAUDE.md, the cross-tool AGENTS.md standard, .cursorrules).
taken & extended: brain/CONSTITUTION.md is that file, but its generated and maintained by the brain
from evidence, not hand-written once and left to rot. its the always-loaded core any worker agent can
be seeded with.

## design stance (where we diverged on purpose)
1. consent is explicit. we learn only from spoken signal. an accepted diff is not a preference.
2. interests over positions. the brain serves the interest behind the instruction, not the literal
   instruction, and may choose a different position.
3. file-first, infra-optional. graphiti/neo4j are heavy. we ship grep+markdown that runs now, with a
   documented graph upgrade, not a day-one dependency.
4. cold multi-lens, not single self-critique. reflexions single self-critique is weaker than my
   independent-converged-review protocol; we use the latter.
5. agent-general, not tool-coupled (P17). the core reasons over codex + claude transcripts; it isnt a
   claude product.
