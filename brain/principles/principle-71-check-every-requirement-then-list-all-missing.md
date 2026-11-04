---
name: principle-71-check-every-requirement-then-list-all-missing
kind: principle
tier: conditional
rule: a tool checks every prerequisite before it does anything and, when any is missing, stops with the whole list - each line naming what is missing and the command that gets it - never one missing thing per run.
interest: [intent-efficiency, intent-comprehension]
confidence: medium
evidence_count: 1
binds: [code]
tells: ["it should check all requirements and then mark whats missing", "dont fail early", "you need: - X - Y"]
---

# P71 - check every requirement, then list all that is missing

## rule
the first step of a script someone else runs is its preflight: every tool on PATH, every login, every
token (and that it is accepted, not only set), every daemon, every file. each failed check prints one
line - what is missing, then how to get it - and the run stops once, after all of them, with the
full list. no check may stop the others.

## why
a fail-fast check turns N missing things into N runs: "imagine you need X and Y, but it fails early
'you need X!' he gets X, then it says 'you need Y!' its annoying". the script is handed to someone
who did not write it ([[intent-comprehension]]) and every extra round trip is theirs
([[intent-efficiency]]).

## how to apply
- collect, then report: each check appends a line; one reporter dies with the list if it is non-empty.
  in bash, feed the reporter by process substitution (`report < <(missing)`), never a pipe, or its
  `die` runs in a subshell and the script carries on.
- check that a credential works, not only that it is set: an expired MLflow token answers a redirect,
  not a refusal, so test for the success code.
- shared checks live in one place both the build and the wrapper source
  ([[principle-31-libraryfy-shared]]).

## verbatim tells
- "if a pre-req ISNT set, then it should say exacty WHAT isnt set. and dont fail early... as in, imagine you need X and Y, but it fails early "you need X!" he gets X, then it says "you need Y!" its annoying, it should check all requirements and then mark whats missing, then say "you need: - X - Y" etc" (2026-11-03, the coworker's one-command MLflow test script)

## anti-pattern
`command -v X || die` repeated per tool; a token check that only tests the variable is non-empty.
