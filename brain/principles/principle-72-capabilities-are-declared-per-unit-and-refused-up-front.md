---
name: principle-72-capabilities-are-declared-per-unit-and-refused-up-front
kind: principle
tier: conditional
rule: when a path works for some units and not others (a backend per tracker), each unit declares a baked-in capability flag, the choice is a flag on the entry script forwarded by its callers, and an unsupported combination is refused at the START with a message that says how to lift it. never hard-code the unit's name, and never make lifting it impossible. the alternate path produces the same real artifact (a normal container), not a demo shortcut.
interest: [intent-craft, intent-control]
confidence: medium
evidence_count: 1
tells: ["bytetrack only, but dont hard-code this. it should instead, be a flag in the build script, and then fwd the flag in the scripts/test_atr...sh script", "refuse it, but at the same time, dont hard code it so hard to where its impossible to make it onnx", "to remove this, you must impl onnx runtime for idehad", "they will all have baked in binary flags checked at beginning", "it should still make a normal docker container and everything, just onnx runtime"]
---

# P72 - declared capability, checked first, refusal names the lift

**Why.** he wants the limit to be a visible, removable fact about each unit, not a name buried in an if.

**How to apply.** flag per unit in its own config; check all units before any work ([[principle-71-check-every-requirement-then-list-all-missing]]); refusal text: "to remove this, you must implement X for Y". requirements that are not real (nvidia-smi required, a build-dir shape limit, checks pinned to one backend's file name) are dropped, not honoured ([[principle-68-a-simplicity-restriction-is-droppable-when-free]]).
