---
name: principle-55-the-run-is-visible
kind: principle
tier: conditional
rule: on a long run, where it stands - the flow stage, the plan phase, what is running, what is left - is a page he can open, hosted locally and kept current at each merge, so knowing it never costs him a question.
interest: [intent-control, intent-comprehension]
confidence: medium
evidence_count: 3
tells: ["what brain stage and plan phase are we at ? can i see ? can you host ?", "and can i get a sneakpeak of the app? like run it right now on main, id like to see visuals", "it looks good, can you update the status page?"]
---

# P55 - the run is visible

## rule
a multi-hour, multi-agent build is opaque from the terminal: merges, reviews and workers scroll
past. its state is one small page - the brain's flow with the current stage marked, the plan's
phases with their status, what is running, what comes next, and the live app's address - served on
his LAN, and updated as each merge lands rather than rebuilt when he asks.

## why
he steers by state ([[intent-control]]) and he asked for it in three questions at once, mid-run:
"what brain stage and plan phase are we at ? can i see ? can you host ?". the run had a preview of
the APP on a port; it had no view of ITSELF.

## how to apply
start the page with the run, not on request; serve it local (no tunnel, no publish unless he asks);
put its address in every report that changes it; one line per item, his words not the machine's.
links: [[principle-48-look-at-the-rendered-output]], [[principle-42-plain-english-questions]].

## verbatim tells
- "what brain stage and plan phase are we at ? can i see ? can you host ?" (2026-10-12, the onboarding
  build, after ~400 commits had landed with no view of the run but the terminal)
- "and can i get a sneakpeak of the app? like run it right now on main, id like to see visuals" (asked to see the live app mid-run)
- "it looks good, can you update the status page?" (approved the page, then had to ask for it to be refreshed: it was not kept current at merges)

## anti-pattern
reporting the state only in terminal prose, so the only way to see the run is to ask and read
scrollback.
