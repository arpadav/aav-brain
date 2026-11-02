---
name: principle-61-private-infra-stays-out-of-tracked-files
kind: principle
tier: conditional
rule: his real hosts, LAN ips, usernames and device ids belong to live runs, untracked plans/ and memory - never to a doc, test or source file git tracks or will track. those carry neutral placeholders (`user@gpu-host`); a real value that gets pushed is a leak he has to rewrite history to undo. his tailnet names count too. what the scan checks and cannot see: `brain-private.py --help`.
interest: [intent-sovereignty, intent-control]
confidence: high
evidence_count: 2
binds: [code]
tells: ["`rg <lan-ip>` and please remove these from docs and tests (fine in plans)", "like can you roll back a commit, edit files, then i commit and force-push? these should not have landed onto the git repo", "actually, its fine. when i merge i will squash anyway. just make the appropriate changes and let me know when done", "also please do NOT embed my ip addresses or my tailscale tailnet url in a test are you stupid?? oh my god... its completely independent from that"]
---

# P61 - private infra stays out of tracked files

## rule
the machine he tests against is his, not the repo's. the real LAN ip, the `user@host` pair, device ids and
the name of his box are fine in the command he runs, in an untracked file under `plans/`, and in memory
(the brain's private data dir). they are not fine in anything git tracks or will track: docs, test
fixtures, expected strings, source - a new test file is untracked until the commit that leaks it. there
the same shape is spelled with a neutral placeholder (`user@gpu-host`, `user@gpu-host.lan`). his tailnet
domain and magicdns names are the same class as a LAN ip.

`bin/check/brain-private.py` enforces it, and `brain-verify.py --run` runs it in VERIFY. what the scan
checks and cannot see: `brain-private.py --help`.

## why
[[intent-sovereignty]]: the permanent record is his, and a pushed value is in the shared repo's history for
good. he found the ip in docs and tests after he had already committed and pushed, and his first move was to
offer a commit rollback and a force-push to get it out - the cost of the slip, paid by him. the agent had
copied the value from his live-run instruction ("i want <host> ssh tried", [[principle-60-device-facing-code-is-gated-by-a-live-run]])
into the fixtures and examples that came out of that run. the instruction to RUN against a real host is not
an instruction to WRITE that host down.

## how to apply
- a live run takes his real target; every doc example and test fixture that falls out of it is written with
  the placeholder from the first draft, including strings derived from the value (a run id built from the host).
- before handing over a diff that touches docs, tests or source, `rg` the tracked files for each private value
  the session used. sweep all tracked files, not only the ones he names; `plans/` is exempt ("fine in plans").
- if the same class of value shows up that he did not name (usernames, device ids, home-dir paths), say so in
  one line; do not decide silently to keep or scrub it ([[principle-01-no-assumptions]]).
- already pushed: fix forward in the working tree and hand it over uncommitted. he squashes on merge, so no
  history rewrite and no menu about how far to rewind ([[principle-33-git-is-not-a-blocker]]).

## verbatim tells
- "`rg <lan-ip>` and please remove these from docs and tests (fine in plans)... like can you roll back a commit, edit files, then i commit and force-push? these should not have landed onto the git repo"
- "actually, its fine. when i merge i will squash anyway. just make the appropriate changes and let me know when done" (his answer to a multi-choice question about how far to roll back)

## anti-pattern
pasting the host from the live-run instruction into a test's expected string and a docs example, pushing it,
and leaving the owner to ask for the removal. a mock that needs "a host" taking his real one instead of an invented one.
