---
name: principle-19-think-in-code-ops
kind: principle
rule: obvious recurring one-off ops are think-in-code skills, not committed scripts. commit a script only when it's a deterministic, re-runnable artifact worth versioning.
interest: [intent-efficiency, intent-craft]
confidence: medium
evidence_count: 3
tells: ["think in code", "removing periods at the end of comments grep", "scripts being used for very obvious skills that can be think in code"]
---

# P19 - think-in-code for the obvious ops

## rule
a trivial op i ask for a lot (e.g. "strip trailing periods from comments", a quick grep/sed sweep)
is a think-in-code SKILL: describe it, run it in the sandbox on demand. do NOT bake a committed
script for every little thing. commit a script ONLY when it's a deterministic builder worth
versioning and diffing (e.g. the corpus extractor).

## why
efficiency + craft: a pile of tiny committed scripts is surface and rot. think-in-code keeps the
op live and the repo clean. P12 (context hygiene) is the same instinct: derive in code, dont dump.

## how to apply
- recurring trivial transform -> skill that runs shell/python in the sandbox. no committed file.
- deterministic re-runnable artifact (the thing brain-meta-learn invokes every refresh) -> commit it,
  in my stack ([[principle-16-my-stack-my-voice]]).
- the line: would i want to version and diff this output over time? yes -> script. no -> skill.

## anti-pattern
committing a 3-line grep as a script. or the reverse: making the canonical corpus builder a
sandbox-only skill with nothing to version.
