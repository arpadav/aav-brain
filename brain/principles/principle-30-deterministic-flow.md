---
name: principle-30-deterministic-flow
kind: principle
tier: narrow
rule: when executing, deterministically follow the execution flow (brain/flow/flow.toml). the FLOW is the sequence; the GRAPH is the context fetcher. they are SEPARATE and must never conflate.
interest: [intent-control, intent-efficiency]
confidence: very-high
evidence_count: 3
tells: ["does it deterministically follow a flow chart", "the brain flow chart where it describes the sequence", "ensure they are separate", "is that conflated with the brain graph context fetcher/manager"]
---

# P30 - deterministic execution flow, separate from the graph

## rule
two distinct artifacts, never conflated:
- the GRAPH = KNOWLEDGE: b-recall answers "which principles apply."
- the FLOW (brain/flow/flow.toml) = the execution sequence. states are work phases, transitions are
  guarded edges. b-walk steps it to answer "what is the next step." it is SEQUENCE.
when executing a task, deterministically FOLLOW the flow: to take any step, query b-walk against
the committed flow file. the brain does not invent the sequence; it reads it.

## why
the flow keeps me the architect of the process ([[intent-control]]) and makes execution reproducible
and leverage-able ([[intent-efficiency]]). a graph that fetched context AND decided sequence would be
two concerns in one artifact - brittle and unauditable. separation by file, vocabulary (principles/edges vs
states/transitions), and call-direction keeps both honest.

## how to apply
- one-directional coupling only: a flow state may reach the graph (its `recall = true` makes b-walk
  print the b-recall call the agent runs to load the relevant principles before the owner runs). the graph NEVER reaches the flow.
- step deterministically: `b-walk -s X -o <outcome> -m <mode>` returns the single next
  state. same input, same next step.
- knowledge never steers sequence: which principle ranks #1 cannot change a transition. transitions depend
  only on (current state, outcome event, guard).
- rebuild + check the flow when it changes: `b-flow`, then `b-flow -c`.

## anti-pattern
describing the flow only as drifting prose/mermaid (un-deterministic, un-checkable). using "node/edge"
to mean both a principle and an execution state. letting the graph decide the next step.
