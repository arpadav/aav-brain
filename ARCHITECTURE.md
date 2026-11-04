# aav-brain architecture

> HUMAN-FACING DOC - nothing reads this at runtime (no skill, agent, or script loads it). it is for a
> person onboarding to the system, or me re-orienting. the runtime sources of truth are
> `brain/CONSTITUTION.md` (tier-1, always loaded), the principles, and `brain/flow/flow.toml`.

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
  brain/principles/*.md      atomic principles (one belief each, [[linked]])
  brain/intents/*.md         interests (the why: positions->interests)
  brain/voice/*.md           how to write/review as me + idiom lexicon

TIER 2.5 - graph: the principles' links as a graph (bin/brainlib/graph.py)

TIER 2.6 - flow = SEQUENCE (the execution flow; "what step is next") - SEPARATE from the graph
  brain/flow/flow.toml       AUTHORED data: entries, states (work phases), transitions (guarded edges)
  stepped directly by bin/run/brain-walk.py (validated on load); bin/store/brain-flow.py populates
  docs/DEV_FLOWCHART.md from docs/templates/DEV_FLOWCHART.md + flow.toml
  cyclic by design (P03): PLAN..PLANGATE, PHASEGATE/VERIFY loop through REMEDIATE until a metric
  threshold holds, only then advance one phase

TIER 2.7 - trace = the brain's own reasoning history (append-only; PRIVATE, out of repo)
  <data>/trace/decisions.jsonl   one line per decision: chosen, what it rejected + why, affects
  written/read by bin/store/brain-trace.py; brain-meta-curate + brain-self-refine consult the decided-AGAINST
  entries to know WHERE a past call was made before re-litigating it

TIER 3 - evidence (machine-derived; PRIVATE, out of repo; regenerate with `b-extract`)
  <data>/evidence/prompts.jsonl   EVERY human turn, bucketed + multi-label classed; nothing dropped
  <data>/evidence/corpus-stats.json   tone %, class counts, sequencing histogram, opening verbs
  <data>/evidence/*.jsonl         back-compat views (rejections, interruptions, approvals, directives, denials)

  (data = `XdgLayout.data` = $XDG_DATA_HOME/aav-brain, i.e. ~/.local/share/aav-brain -> the logs/ submodule. the raw
   trace + prompts live in a SEPARATE private repo (aav-brain-logs), never in this repo's history.)
```

the GRAPH and the FLOW are two distinct deterministic artifacts, never conflated (P30). the graph is
KNOWLEDGE (principles/edges) answering "which principles apply"; the flow is SEQUENCE (states/transitions)
answering "what is the next step". coupling is one-directional: a flow state with `recall = true` makes
b-walk print the b-recall call the agent runs to load context; the graph never reaches the flow.
file-first, zero servers; the graph's export and neo4j: see schema/optional-graph.md.

## scope: what is and is not the brain

the brain is `brain/` (the principles, graph and flow) plus the scripts in `bin/`. `agentic-files/` is a
SEPARATE entity that merely hosts some brain skills and agents alongside unrelated ones used on other
machines and in other projects. do not audit, prune, or reason about what lives there as if it were
brain territory - an agent with zero dispatches in this repo's transcripts may be in daily use
elsewhere.

## 2. the acting suite (in agentic-files/)

skills are the unit (P18). a null agent + a loaded skill = a standalone specialist. the suite is FIVE
user-callable ENTRY skills + six `brain-meta-*` machinery skills + the agents (categorized under
`agentic-files/agents/{brain,general,lang/rust,style}`). you only ever call the entries; the
`brain-meta-` prefix marks "machinery, dont call directly." skills are the universal SKILL.md across
claude / codex / ~/.agents; agents are claude `.md` + a codex `.toml` compiled into `.generated/`.

every skill EXECUTES the bundled scripts rather than reading flow.toml or the principles and reasoning by hand -
running a script keeps its code out of context and is deterministic. module.nix writes a command for
every brain script (`Layout.scripts` says which file is one) into `~/.local/bin`, named `b-` plus its
stem less `brain-` (`brain-walk.py` -> `b-walk`, `brain-find.py` -> `b-find`); that directory reaches
PATH from the home config (his `home.sessionPath`), not from this module. module.nix also exports the
brain root as `$AAV_BRAIN` and its short alias `$AVB`, which the skills and agents read a brain file
off (`$AVB/brain/CONSTITUTION.md`), so a skill calls `b-walk -s ...` with no setup line and no
hardcoded path on any machine (P32). an agent starts after the switch that exports both, so neither
needs a fallback; the commands do not read them at all, each finds the root from its own location. every
flag has a one-letter short form and keeps its long form as an alias; the first `b-walk` of a session
prints the legend of every command's flags, and `b-walk -l` reprints it. `b-find` prints the root, and
`eval "$(b-find -e)"` sets both exports in a shell of his that predates the switch.

the ENTRIES (call these) are the `[[entries]]` rows of flow.toml - each names its skill, the node it
enters the unified flow at, and the mode it walks in; docs/DEV_FLOWCHART.md lists them.

two more skills sit OUTSIDE the flow: `brain-measure`, user-callable, runs the 25 eval tasks with the
brain's principles and without, and hands him one file to grade (`eval/brain-eval.py`); `brain-open-items`
writes, stamps and watches the P66 open items, its script beside its SKILL.md, keeping each in step
with its todo when `life` is on PATH.

the ENGINE + the MACHINERY (loaded BY an entry or the flow, never called directly):
| brain-meta-* | role |
|---|---|
| brain-meta-drive | the shared traversal ENGINE: steps flow.toml, dispatches each owner, loops the gates. every entry traverses with this one trampoline (P31) |
| brain-meta-intent | position -> interest; surface ambiguity; ask-first before sanction |
| brain-meta-author-prompt | write worker prompts in my voice + intent |
| brain-meta-style | review as me (plan lens + style lens), cite principles; runs `b-fmt` |
| brain-meta-curate | self-editing memory: corrections -> update the store; consults the trace |
| brain-meta-commit | prepare the git record, never publish it |
| brain-learner (agent) | dispatched at DONE: re-extract + curate + check + PRUNE; runs `b-extract` |

agents (cold dispatch, separate window - a distinct category, NOT `brain-meta-*`):
| agent | role |
|---|---|
| brain-review-gate | cold/unguided multi-lens review of a phase diff; converge; single-nit-blocking |
| brain-verifier | anti-fabrication: build/test/bench honestly, read errors |

## 3. the control loop (entry + shared engine, a trampoline over the flow)

the entries are THIN: each reconstructs its region's state, sets a start node + a regime, and hands
the walk to the ONE shared engine, brain-meta-drive (P31). the engine does not invent the sequence - it
STEPS the flow deterministically: each iteration asks b-walk for the current state (owner + recall
call), runs the owner, and feeds the outcome event back to b-walk for the next state. the brain
follows the flowchart because it must query flow.toml to take a step (P30).

```
   <entry> = a flow.toml [[entries]] row: skill @ state, walking in its mode
     state, regime := reconstruct THIS region's state; set the entry node + ask-first|execute-through
     load brain-meta-drive, run it from <state>:

   brain-meta-drive (the shared engine - the trampoline):
     loop:
       step       := b-walk -s <id> -m <m>             # data says: owner + recall call
       principles := b-recall(task) if step.recall     # the ONE call into the graph (context)
       event      := run(step.owner, principles)       # a brain-meta-* skill OR a cold agent does the work
       state      := b-walk -s <id> -o <event> -m <m>  # data says the next state; brain doesnt invent it
     until terminal; stop+ask on BLOCKED/ASK
```

the flow is MULTI-ENTRY: one graph, one start node per entry, regime read FROM the entry (not inferred from
crossing SANCTION - review and self-refine reach a terminal without it). reconstruction is per-entry
(execute rebuilds from the sanctioned plan + git; self-refine from its selection-state), the engine reconstructs
nothing. owners are the brain-meta-* skills / cold agents: brain-meta-author-prompt writes the worker
prompt; the brain-verifier + brain-review-gate agents gate cold; brain-meta-style does the style pass;
brain-meta-commit prepares the record; brain-meta-curate learns. the critics are cold and independent
(not a single self-critique) because i distrust a single confident pass (P03, P04). the boundary state
(SANCTION) is the one flip from ask-first to execute-through, on the plan->build path.

## 4. data flow end to end
1. learn: `b-extract` mines ~/.codex (sessions + archived_sessions) + ~/.claude/projects ->
   tier-3 evidence (every turn). brain-meta-curate distills durable lessons into tier-2 principles. explicit
   signal only.
2. recall: a task arrives -> b-recall returns the principles relevant to the task (bin/brainlib/recall.py)
   -> they become the working context. small, targeted (context hygiene, P12).
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
- the store is plain markdown + the brainlib library + the tools under `bin/`, all importing brainlib.
  no services to start.

## 6. how to use it
see README.md for the quickstart. the entrypoints (the only skills you call):
- /brain-plan <idea>: plan this new thing (or a change) my way, to sanction.
- /brain-execute: build a sanctioned plan to DONE - and "continue" / "resume" picks it back up.
- /brain-edit <change>: one small follow-up edit to what that build produced, without replanning it.
- /brain-review: cold multi-lens review of the current diff.
- /brain-self-refine: turn the review lens on the brain itself.
