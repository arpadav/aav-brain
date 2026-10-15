---
name: principle-39-style-contract
kind: principle
tier: conditional
rule: every language written gets its style resolved from the aav-style spec BEFORE code exists, and the STYLE gate is always required - it proves the result with brain-fmt.py --gate rather than asserting it. the contract lives here, not in a plan, so a plan from any source inherits it.
interest: [intent-craft]
confidence: very-high
evidence_count: 5
binds: [code]
tells: ["they do not follow my style guide", "adhering to my style should be baked into the brain", "i always have to manually do it afterwards", "it should ALWAYS be required, unless i explicitly ask against it", "and you will do a style pass at the end? seeing a lot of issues on the rust side that dont adhere to my style. note that this should be at the END once its ALL DONE", "please do a style pass on the git diff compared to main (+4.7k -200 lines). shell and python and all", "for phase 1's style pass in havoc-ml, which rule wins? -> My style, touched lines"]
---

# P39 - the style contract, and the gate that proves it

## rule
the style spec is not advice given at the end of a build. it is a contract resolved before the first
line and enforced by a gate that can fail.

**it lives on this card, deliberately not in the plan.** a plan written elsewhere - by him, by another
tool, by a previous session - carries no style section, and if the contract lived in `brain-plan` then
executing a foreign plan would silently skip it. the flow reaches this card regardless of where the
plan came from. a plan MAY name an exception and override; its silence changes nothing.

## the language registry
`agentic-files/agents/style/aav-style-separators.md` §0 carries the table. it is language-INDEPENDENT
and already names Rust, Python, C/C++/CUDA, TypeScript and Bash with the comment marker, doc-comment
form, import stanza and formatter for each. **resolve the row before writing, not after.** a language
with no row is a question for him, never a guess - which is [[principle-06-idiomatic-per-language]]
applied to style rather than to the build toolchain.

## the four lenses own the spec; the flow dispatches them
`aav-style-separators`, `aav-style-docs`, `aav-style-imports`, `aav-style-items`. before this card they
were named in ZERO flow states and ZERO skills - four agent files holding the spec that nothing ever
called. they are now the STYLE state's dispatched owners, alongside `brain-meta-style:style`.

## the gate must be falsifiable
STYLE previously had a single outbound event, `styled`. it was the only substantive state in the build
region that could not fail - every other one loops until a metric holds. so a hollow pass and a
thorough one were indistinguishable to the machine, and "the style pass always runs" was true and
meaningless simultaneously.

it now emits `unstyled` and loops. `brain-fmt.py --gate` supplies the countable half:

- function bodies with zero local separators (§11, the spec's own "most important part")
- a blank line following a separator (the spec says never)
- a global separator label outside the closed whitelist
- the language's formatter clean, run LAST

what a script cannot judge - whether a local separator is NAMED well - stays with the lenses.

## why this card exists at all
measured on a seven-variant CUDA suite the brain had just declared complete:

```
local separators inside functions      0   across 283 function bodies
blank line after a separator          53
global labels outside the whitelist  109
```

and the reason the end-of-build pass did not catch it: `brain-fmt.py`'s rewriting path was hardcoded
to `#`, so it silently skipped every `.cu` and `.cpp` handed to it. it reported "10 file(s) rewritten"
having touched only the python. **a style tool that cannot see the language reports success by
saying nothing.**

## how to apply
- resolve the language row at INTENT, before the plan, not at STYLE.
- STYLE is always required. only an explicit instruction against it skips it.
- run `brain-fmt.py --gate` and let the number decide; do not emit `styled` on judgement.
- the scope of a style pass is whatever he points it at, in every language in that diff: "please do a style pass
  on the git diff compared to main (+4.7k -200 lines). shell and python and all". a python repo with posix sh
  templates and a Dockerfile gets all three passes, not just the language the brain thinks of first.
- while the pass runs in a scratch worktree, say so when he asks and keep his checkout untouched until the one
  apply command ([[principle-09-git-sovereignty]]): "note you are making style pass on scratchpad and not main
  branch, yes?"
- when the gate and his own reference code disagree, that is a question for him, not a threshold to
  tune - tuning the bar until it passes is the failure [[principle-04-anti-fabrication]] names.
- in a shared repo whose own rules differ (havoc-ml's AGENTS.md: "keep comments minimal"), ask once; he chose
  his style on the lines the change writes ONLY. the lenses review the diff hunks; a rule that needs untouched
  lines is reported, never applied; `brain-fmt.py` changes on untouched lines are out of scope. calibrate to
  HIS code in that repo, not the abstract spec: his havoc-ml `deploy/` docstrings end sentences with periods,
  so a lens asking to strip them on touched lines only was rejected (it would mix styles in one docstring).
