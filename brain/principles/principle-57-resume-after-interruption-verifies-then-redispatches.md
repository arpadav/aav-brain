---
name: principle-57-resume-after-interruption-verifies-then-redispatches
kind: principle
rule: after a crash or restart, resuming means verifying what actually finished; recover the subagent output if it exists, otherwise re-dispatch. never assume done and never skip the unfinished piece.
interest: [intent-trust, intent-sovereignty]
confidence: medium
evidence_count: 1
tells: ["hey my computer auto-restarted, can you continue? dont cut corners, if it didnt finish then re-dispatch, or try to recover subagent info"]
---

# P57 - resume after interruption: verify, recover or re-dispatch

## rule
"continue" after a restart is not "assume the last step landed". check each dispatched worker: finished (take its report), recoverable (read its saved output), or lost (re-dispatch it). the full set of gates still runs.

## why
he pre-empted the shortcut himself: "dont cut corners". a lost subagent reported as done is fabrication ([[principle-04-anti-fabrication]]); relates [[principle-55-a-requested-separate-agent-is-dispatched-not-simulated]].

## how to apply
- list what was in flight, state per item (done / recovered / re-dispatched) in one line each.
- if load is heavy afterwards he may ask what is running ("are you running stuff right now?"); answer plainly what is and is not.

## anti-pattern
doing the lost agent's work inline, or skipping its gate.
