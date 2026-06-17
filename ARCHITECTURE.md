# aav-brain architecture

> HUMAN-FACING DOC - nothing reads this at runtime (no skill, agent, or script loads it). it is for a
> person onboarding to the system, or me re-orienting. the runtime sources of truth are
> `brain/CONSTITUTION.md` (tier-1, always loaded), the principle cards, and `brain/flow/flow.toml`.

a second brain for my dev work. it learns how i plan, review, write, and push back from my real
agent transcripts (codex + claude), then acts as me: agrees/disagrees with other agents work, writes
prompts in my voice, supervises a plan by dispatching other agents, and holds my standards.

ONE repo, two halves by ROLE (not by repo):
- the TOOL: the knowledge store (`brain/`), the docs, and the tooling (`bin/`).
- the ACTING SUITE (`agentic-files/`): the skills + agents that act, linked into claude + codex by
  home-manager. private memory (trace + evidence) is the `logs/` submodule - its content lives in a
  separate private repo, never in this history.

## 1. memory, tiered (after memgpt/letta)

```
TIER 1 - core (always loaded when the brain acts)
  brain/CONSTITUTION.md      prime rule, who i am, the operating loop, the hard rules, voice

TIER 2 - corpus (retrieved on demand via the graph)
  brain/principles/*.md      atomic principle cards (one belief each, [[linked]])
  brain/intents/*.md         interest cards (the why: positions->interests)
  brain/voice/*.md           how to write/review as me + idiom lexicon

TIER 2.5 - graph = CONTEXT (the knowledge graph; "which principles apply")
  brain/graph/graph.json     nodes (principle + interest) + edges (serves/served_by/relates/tension)
  brain/graph/graph.cypher   optional neo4j export for a visual; nothing depends on neo4j
  built by bin/brain-graph.py, walked by bin/brain-recall.py

TIER 2.6 - flow = SEQUENCE (the execution flow; "what step is next") - SEPARATE from the graph
  brain/flow/flow.toml       AUTHORED data: states (work phases) + transitions (guarded edges)
  brain/flow/flow.json       the built, validated machine; committed
  built by bin/brain-flow.py (also generates docs/DEV_FLOWCHART.md), stepped by bin/brain-walk.py
  cyclic by design (P03): PLAN..PLANGATE, PHASEGATE/VERIFY loop through REMEDIATE until a metric
  threshold holds, only then advance one phase

TIER 2.7 - trace = the brain's own reasoning history (append-only; PRIVATE, out of repo)
  <find_data>/trace/decisions.jsonl   one line per decision: chosen, what it rejected + why, affects
  written/read by bin/brain-trace.py; brain-meta-curate + brain-self-refine consult the decided-AGAINST
  entries to know WHERE a past call was made before re-litigating it

TIER 3 - evidence (machine-derived; PRIVATE, out of repo; regenerate with bin/brain-extract.py)
  <find_data>/evidence/prompts.jsonl   EVERY human turn, bucketed + multi-label classed; nothing dropped
  <find_data>/evidence/corpus-stats.json   tone %, class counts, sequencing histogram, opening verbs
  <find_data>/evidence/*.jsonl         back-compat views (rejections, interruptions, approvals, directives, denials)

  (find_data = $XDG_DATA_HOME/aav-brain, i.e. ~/.local/share/aav-brain -> the logs/ submodule. the raw
   trace + prompts live in a SEPARATE private repo (aav-brain-logs), never in this repo's history.)
```

the GRAPH and the FLOW are two distinct deterministic artifacts, never conflated (P30). the graph is
KNOWLEDGE (cards/edges) answering "which principles apply"; the flow is SEQUENCE (states/transitions)
answering "what is the next step". coupling is one-directional: a flow state with `recall: true` CALLS
brain-recall to load context; the graph never calls the flow. both are byte-identical on re-run and
`--check`-guarded (`brain-graph.py --check`, `brain-flow.py --check`). file-first, zero servers. neo4j
is an optional export only; see schema/optional-graph.md.

## 2. the acting suite (in agentic-files/)

skills are the unit (P18). a null agent + a loaded skill = a standalone specialist. the suite is FOUR
user-callable ENTRY skills + eight `brain-meta-*` machinery skills + the agents (categorized under
`agentic-files/agents/{brain,general,lang/rust,custom}`). you only ever call the four entries; the
`brain-meta-` prefix marks "machinery, dont call directly." skills are the universal SKILL.md across
claude / codex / ~/.agents; agents are claude `.md` + a codex `.toml` compiled into `.generated/`.

every skill EXECUTES the bundled scripts rather than reading flow.json/graph.json and reasoning by hand -
running a script keeps its code out of context and is deterministic. the discovery preamble
(`eval "$(brain-find --export)"`, brain-find on PATH) sets `$AAV_BRAIN` with no hardcoded path on any
machine; the skill then invokes `$AAV_BRAIN/bin/<script>.py` - no layout-assuming per-skill symlink (P32).

the 4 ENTRIES (call these) - each enters the unified flow at its own node and walks to a terminal:
| entry | enters flow at | what it does |
|---|---|---|
| brain-plan | IDEATION | small+verbose plan with a worked example, traced through it (PLANPROBE), to plans/. also new-project kickoff (interrogate the spec first). |
| brain-execute | IMPL | build a sanctioned plan to DONE; "continue" / "resume" re-invokes it and rebuilds state |
| brain-review | REVIEW | cold multi-lens review of the current diff, into the shared gate loop |
| brain-self-refine | SR_SCAN | turn the review lens on the brain itself; findings+questions, then edit |

the ENGINE + the MACHINERY (loaded BY an entry or the flow, never called directly):
| brain-meta-* | role |
|---|---|
| brain-meta-drive | the shared traversal ENGINE: steps flow.json, dispatches each owner, loops the gates. all 4 entries traverse with this one trampoline (P31) |
| brain-meta-recall | retrieval: EXECUTE brain-recall.py over the graph (the skill; brain-recall.py is the script) |
| brain-meta-intent | position -> interest; surface ambiguity; ask-first before sanction |
| brain-meta-author-prompt | write worker prompts in my voice + intent |
| brain-meta-style | review as me (plan lens + style lens), cite cards; runs brain-fmt.py |
| brain-meta-curate | self-editing memory: corrections -> update the store; consults the trace |
| brain-meta-commit | prepare the git record, never publish it |
| brain-meta-learn | re-extract + curate; calls brain-extract.py |

agents (cold dispatch, separate window - a distinct category, NOT `brain-meta-*`):
| agent | role |
|---|---|
| brain-review-gate | cold/unguided multi-lens review of a phase diff; converge; single-nit-blocking |
| brain-verifier | anti-fabrication: build/test/bench honestly, read errors |

## 3. the control loop (entry + shared engine, a trampoline over the flow)

the four entries are THIN: each reconstructs its region's state, sets a start node + a regime, and hands
the walk to the ONE shared engine, brain-meta-drive (P31). the engine does not invent the sequence - it
STEPS the flow deterministically: each iteration asks brain-walk for the current state (owner + recall
flag), runs the owner, and feeds the outcome event back to brain-walk for the next state. the brain
follows the flowchart because it must query flow.json to take a step (P30).

```
   <entry> = brain-plan@IDEATION | brain-execute@IMPL | brain-review@REVIEW | brain-self-refine@SR_SCAN
     state, regime := reconstruct THIS region's state; set the entry node + ask-first|execute-through
     load brain-meta-drive, run it from <state>:

   brain-meta-drive (the shared engine - the trampoline):
     loop:
       step  := brain-walk --state <id>                  # data says: owner + recall flag
       cards := brain-recall(task) if step.recall         # the ONE call into the graph (context)
       event := run(step.owner, cards)                    # a brain-meta-* skill OR a cold agent does the work
       state := brain-walk --state <id> --on <event>      # data says the next state; brain doesnt invent it
     until terminal; stop+ask on BLOCKED/ASK
```

the flow is MULTI-ENTRY: one graph, four start nodes, regime read FROM the entry (not inferred from
crossing SANCTION - review and self-refine reach a terminal without it). reconstruction is per-entry
(execute rebuilds from plans/+git; self-refine from its selection-state), the engine reconstructs
nothing. owners are the brain-meta-* skills / cold agents: brain-meta-author-prompt writes the worker
prompt; the brain-verifier + brain-review-gate agents gate cold; brain-meta-style does the style pass;
brain-meta-commit prepares the record; brain-meta-curate learns. the critics are cold and independent
(not a single self-critique) because i distrust a single confident pass (P03, P04). the boundary state
(SANCTION) is the one flip from ask-first to execute-through, on the plan->build path.

## 4. data flow end to end
1. learn: bin/brain-extract.py mines ~/.codex (sessions + archived_sessions) + ~/.claude/projects ->
   tier-3 evidence (every turn). brain-meta-curate distills durable lessons into tier-2 cards, then
   bin/brain-graph.py rebuilds the graph. explicit signal only.
2. recall: a task arrives -> brain-recall walks the graph and returns the relevant cards -> they
   become the working context. small, targeted (context hygiene, P12).
3. act: brain-execute drives the loop, dispatching workers via brain-meta-author-prompt, gating with the
   brain-review-gate + brain-verifier agents.
4. record: brain-meta-commit prepares the commit. i run it.
5. curate: brain-meta-curate writes back what was learned this run, logging each call to the decision
   trace. the store sharpens.
6. self-refine (the meta-loop): brain-self-refine scans the store, asks the brain what i'd
   interrogate, brings findings+questions (not a plan), and on my selection edits the brain + logs to
   the trace. this is P29 pointed inward - the brain reviewing the brain.

## 5. isolation
- ONE repo, separated by role: acting code under `agentic-files/`, doctrine under `brain/`, tooling
  under `bin/`. private memory is the `logs/` submodule (content in a separate private repo).
- the agents it bundles are DECOUPLED + general-purpose: they reference the current repo's layout +
  conventions, never a specific project (the semantic-architecture reviewer discovers the repo's
  crates/CLAUDE.md instead of hardcoding them; no machine-specific paths, P32).
- the store is plain markdown + the brainlib library + the tools (extract, graph, recall, flow, walk,
  fmt, cards, trace, find, compile), all importing brainlib. no services to start.

## 6. how to use it
see README.md for the quickstart. the four entrypoints (the only skills you call):
- /brain-plan <idea>: plan this new thing (or a change) my way, to sanction.
- /brain-execute: build a sanctioned plan to DONE - and "continue" / "resume" picks it back up.
- /brain-review: cold multi-lens review of the current diff.
- /brain-self-refine: turn the review lens on the brain itself.
