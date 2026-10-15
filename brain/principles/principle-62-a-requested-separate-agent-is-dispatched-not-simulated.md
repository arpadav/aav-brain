---
name: principle-62-a-requested-separate-agent-is-dispatched-not-simulated
kind: principle
tier: conditional
rule: when he asks for a separate subagent to do a piece of work (a search, a review), the orchestrator dispatches that agent and relays between them; it never absorbs the work into its own context or lets another worker do it inline.
interest: [intent-sovereignty, intent-trust]
confidence: medium
evidence_count: 1
tells: ["i asked explore: 'send out a seperate subagent to potentially find instances of that. there might not be, so dont make it up' but now its trying to do it itself, tell it to stop and you spawn that agent and make them talk"]
---

# P62 - a requested separate agent is dispatched, not simulated

## rule
"send a separate subagent" is a method instruction, not a suggestion. the agent that received it either spawns the independent agent or hands the request up to whoever can; it does not do the search itself. when a worker lacks a dispatch tool, the parent spawns the agent and carries messages between them.

## why
the separateness is the point: a cold finder has no stake in the first agent's conclusions, and he also warned "there might not be, so dont make it up" - an agent that does its own search is invested in finding something. ties to [[principle-03-review-gate]] and [[principle-04-anti-fabrication]].

## how to apply
- a worker says it cannot dispatch: parent spawns the finder, forwards the worker's scope, and relays results.
- a clean "none found" from the independent agent is a valid outcome; do not pad.

## anti-pattern
the explorer quietly doing the second search "to save a step".
