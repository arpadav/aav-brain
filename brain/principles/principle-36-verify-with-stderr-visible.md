---
name: principle-36-verify-with-stderr-visible
kind: principle
rule: a verification step must never suppress stderr or ignore an exit code. if you cannot see the failure channel, you are not verifying - you are guessing with extra steps.
interest: [intent-trust]
confidence: high
evidence_count: 2
tells: ["it was silently failing while I reported it working", "EXIT=$? after a pipe"]
---

# P36 - verify with the failure channel visible

## rule
when the point of a command is to prove something works:
- never `2>/dev/null`, never `>/dev/null 2>&1`
- never read `$?` after a pipe - that is the exit code of the LAST stage, not yours
- assert on the artifact the command was supposed to produce, not on the absence of
  visible complaint

convenience-silencing is fine while exploring. it is never fine while verifying.

## why
`resume index >/dev/null 2>&1` was reported as passing across several rounds while it
raised a `TypeError` every time; the failure only surfaced when a later command needed
its output. separately, `cmd | tail -3; echo "EXIT=$?"` printed `EXIT=0` for a command
that exits 1, because `tail` succeeded. both produced confident, false reports
([[intent-trust]], [[principle-04-anti-fabrication]]).

## how to apply
- verification commands run bare, output visible.
- check the artifact: file exists, count matches, text present - not "no error printed".
- for a pipeline, capture the code before piping, or use `PIPESTATUS`.

## anti-pattern
a green verification block whose every line hid the channel that would have shown it
red.
