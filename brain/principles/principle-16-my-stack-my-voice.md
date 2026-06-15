---
name: principle-16-my-stack-my-voice
kind: principle
rule: tooling is in my stack (rust or bash, never node/mjs); tooling, scripts, architecture and docs are in my voice. agent-speak only in the agent/skill .md peripherals.
interest: [intent-craft, intent-comprehension]
confidence: very-high
evidence_count: 35
tells: ["make a bashscript", "use uv for python venv", "do NOT fluff wording - be an engineer", "get to the damn point"]
---

# P16 - my stack, my voice

## rule
1. scripts in my stack. evidence: script-creation asks by language = rust 21, bash 11, python 2,
   node 0. ".mjs" in my whole history = 0. so: rust for sharp tools, bash for glue, python (via uv)
   for data munging. never node/mjs/npm.
2. my voice in all tooling, scripts, architecture, docs. lowercase, terse, numbered, CAPS for hard
   constraints, name exact things, end on the action. no em-dash essays. no grandiose words
   no grandiose words, no em-dash essays, no third-person bio prose about me.
3. agent-speak is fine ONLY inside the agent/skill .md files. those are peripherals. everything
   else is mine.

## why
the brain is supposed to read like i wrote it. off-stack scripts and essay prose are a tell that it
didnt. craft + comprehension: i can read and trust my own idiom, not a node dependency and a
marketing paragraph.

## how to apply
- new tool? pick rust or bash first. python only for data, run via uv, stdlib, no project.
- writing a doc/comment? write it the way i write a prompt. if it has an em-dash essay seam, cut it.
- reviewing the brain? flag any node/mjs and any essay prose immediately.

## anti-pattern
a node `.mjs` script (i never write those). docs written about me in third person ("he is the
architect"). em-dashes as connective tissue. emoji in a title.
