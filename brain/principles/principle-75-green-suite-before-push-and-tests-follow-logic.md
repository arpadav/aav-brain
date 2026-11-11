---
name: principle-75-green-suite-before-push-and-tests-follow-logic
kind: principle
tier: conditional
rule: nothing is pushed or PR'd while the project's full test command fails. a failing test is read, not patched: decide whether the behavior really changed. a test pinned to an old spelling or call shape of an ability that still exists is deleted or updated, with no compat shim; a test whose expected RESULT changed (fn(2) was 6, now 5) is a logical break and is reported as one. only then push.
interest: [intent-trust, intent-craft]
confidence: medium
evidence_count: 2
tells: ["uv run poe test will succeed. meaning, dont push where it fails. run, figure out if any fail why fail. dont just naively patch, but see if behavior is breaking, etc. fix properly. only after fix you push and pr", "if the same ability is capable with new ops, then new ops are fine. i dont expect backwards compat just for a simple call... straight up delete tests if they are old"]
---

# P75 - green suite before push; tests follow the API, results are the contract

## rule
1. the push (and PR) waits for the project's own full test command to pass.
2. each failure is classified before it is touched: old API shape (delete or update the test, no
   backwards-compat layer) versus changed logical result (a breaking change - say so, do not bend the
   test to the new number).
3. fix properly, then push. this is the permission-to-push gate only; the run still batches test
   runs to the end ([[principle-53-rigor-scales-with-the-change]]) and the push itself stays his
   to ask for ([[principle-09-git-sovereignty]]).

## why
a push on a red suite hands him a failure he has to triage; a naive patch hides a real behavior
change. the dividing line is his: an interface moved is not a regression, a result moved is.

## how to apply
- run the full command once, read every failure, write the verdict per test, then edit.
- never keep an old call spelling alive just so an old test passes ([[principle-14-minimal-surface]]).
