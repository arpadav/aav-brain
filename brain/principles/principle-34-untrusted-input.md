---
name: principle-34-untrusted-input
kind: principle
rule: treat every filename, path, posting, plan, and cache line as attacker-controlled. never let data reach a shell word-expansion, a subprocess string, or a markup document without being neutralised at the boundary.
interest: [intent-trust, intent-craft]
confidence: high
evidence_count: 3
tells: ["arbitrary code execution on TAB", "compgen -W word-expands", "plans are agent-authored"]
---

# P34 - data is untrusted, especially data I generated

## rule
anything not typed by him this turn is untrusted input: filenames, cache files, job
postings, patch plans, sidecars. the fact that an agent produced it makes it MORE
suspect, not less - an agent chose the name, so an agent chose the payload.

neutralise at the boundary, never at the use site:
- **shell**: never `compgen -W "$var"`, never an unquoted `$(...)` in a completion.
  read with `readarray -t` and filter in-shell.
- **subprocess**: argument lists, never a shell string.
- **markup**: strip or escape control characters before writing XML/TOML/JSON.
- **paths**: containment-check against a known root before any write or delete.

## why
this was not theoretical. a bash completion shipped in this repo executed
`$(touch /tmp/PWNED)` embedded in a resume filename, on TAB. the chain was entirely
in-house: the skill let an agent name the output, `resume index` wrote it to
`names.txt`, completion word-expanded it. every link looked benign alone
([[intent-trust]]).

## how to apply
- at every boundary ask "who could have written this string, and what happens if it
  contains `$(`, a newline, `../`, or `\x00`?"
- prefer the API that cannot interpolate (`readarray`, arg lists, a real serialiser)
  over remembering to quote.
- containment before writes: `sweep` refuses to leave the vault; `patch` must too.

## orthogonality
[[principle-08-read-source-and-error]] is about believing the error over your model;
P34 is about not trusting the *data*. [[principle-04-anti-fabrication]] governs what
you report; P34 governs what you consume.

## anti-pattern
"it is only my own filenames" - that is exactly the case that shipped an RCE. and a
store with no security card at all: `brain-recall "security untrusted input shell
injection"` returned **no matching cards** while this bug was live.
