---
name: principle-66-open-items-are-one-file-each
kind: principle
tier: conditional
rule: a decision that outlives the session is one file, plans/open-items/<ID>-<slug>.md - title states the problem in one line, then What / Issue / Decisions (recommended option plus an A/B/C table) / Your call, every term defined with "e.g." on first use, and a sha256 footer so an edit by him is detected, not asked about.
interest: [intent-comprehension, intent-efficiency, intent-control]
confidence: medium
evidence_count: 9
binds: [plans]
tells: ["i like to have `open-items` folder no `plans/open-items/*.md` where each file is an open item", "it breaks down the problem, defines jargon, and keeps a sha256 sum/hash of the doc to see when ive editted it at the bottom", "then based off those, it can make a plan and execute on open items", "ask me if there is anything blocking or open decisions to be made"]
---

# P66 - open items are one file each

## rule
one file per open item under `plans/open-items/`, named `<ID>-<slug>.md`. the ID keeps the
project's category-letter scheme (Q01, P03, DES-48). the shape:

    # <ID>: <the problem in one sentence>
    The issue is with <thing> (e.g. <a concrete instance>).
    ## What      - how it works today, with a minimal example and its real output
    ## Issue     - what goes wrong, shown by a run; his prior words quoted and dated
    ## Decisions - **Recommended: X.** one-line reason; an A/B/C table; the deciding question
    ## Your call - empty; he writes here
    <!-- sha256: ... -->

## why
[[intent-comprehension]]: he decides without holding the context; each item defines its own terms
("(e.g. ...)" on first use) and shows the behavior by a run, not a claim ([[principle-04-anti-fabrication]]).
[[intent-efficiency]]: the footer hash tells the brain which items he edited, so no one asks
"did you answer Q07?". [[intent-control]]: the call is his, written in his file.

## how to apply
- write, then `brain-open-items.py stamp <file>`. at plan or execute start, `brain-open-items.py
  status`: `edited` items carry his answer and are the input to the plan.
- a resolved item is not archived: CLEANUP folds the decision into the docs it affects, deletes the
  file and the todo bullet that pointed at it ([[principle-56-close-out-housekeeping]]).
- the register is [[principle-57-user-docs-are-an-icd]]; options follow
  [[principle-65-numbered-recommendations-get-one-word-replies]].

## anti-pattern
open decisions buried in a plan's section 6, or one OPEN.md holding forty items he must scroll and
cannot mark individually.
