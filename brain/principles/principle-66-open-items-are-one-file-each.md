---
name: principle-66-open-items-are-one-file-each
kind: principle
tier: conditional
rule: a decision or bug that outlives the session is one file, plans/open-items/<ID>-<slug>.md, written in plain-text-legible markdown at the size the problem needs - a simple problem is one sentence of problem and one of fix; only a complex one gets setup, an example or a truth table - ending in "Your call" and a sha256 footer so his edit is detected, not asked about.
interest: [intent-comprehension, intent-efficiency, intent-control]
confidence: medium
evidence_count: 12
binds: [plans]
tells: ["make initial plan, make assumptions and open items in a folder", "i like to have `open-items` folder no `plans/open-items/*.md` where each file is an open item", "it breaks down the problem, defines jargon, and keeps a sha256 sum/hash of the doc to see when ive editted it at the bottom", "then based off those, it can make a plan and execute on open items", "ask me if there is anything blocking or open decisions to be made", "execute the plan, keeping open items open, and designing/executing around them to be filled later. unless there is a huge blocker, then ask", "still way too wordy", "i want ONLY markdown which is legible via plaintext", "STOP trying to fit everything inside of the same sized box", "stop auto-truncating sentences"]
---

# P66 - open items are one file each, sized to the problem

## rule

One file per open item under `plans/open-items/`, named `<ID>-<slug>.md`. The ID keeps the project's scheme (ICD-07, HOS-02, Q01).

The file is as small as the problem allows. There is no fixed set of sections to fill.

A simple problem is two sentences. Example: "ICD 5.1.2.2 says range is withheld without pose, but ICD 6.2 says model range needs no pose. 6.2 is assumed correct, because the model computes range from pixels alone. Fix 5.1.2.2: replace `calibration, camera height, or pose` with `the inputs its method needs`."

A complex problem gets setup, built from short sentences. For a chain of events, explain each part, then what goes wrong together, then a concrete example. For example: "The gate holds a frame for 50 ms. The timer drops a track after 2 s. Together they race: a drop can publish before a frame captured earlier. Example: frame at t=1.99 s arrives at 2.03 s, after the drop stamped 2.00 s."

For a set of conditions, use a plain-text truth table:

    pose  calibration  height | range
    yes   yes          yes    | valid
    no    yes          yes    | withheld

Every file ends with:

    ## Your call

    <!-- sha256: ... -->

## format rules

- Plain-text legible only. No markdown tables, no inline HTML, no bold-in-cells. Headings, short bullets, code blocks and indented blocks are fine.
- One sentence states one thing. Do not chain clauses with semicolons or parentheses to fit more in.
- Do not hard-wrap. A paragraph is one line; only a new paragraph gets a newline. His viewer wraps.
- Define a term only if he would not know it, inline and once.
- A proposed fix is concrete: the exact text, diff or command, not a description of one.

## how to apply

- Write, then stamp the sha256 footer (`brain-open-items.py stamp <file>`). At plan or execute start, run `brain-open-items.py status`: an edited item carries his answer and is input to the plan.
- Executing with items still open is his call, and he has made it ("execute the plan, keeping open items open, and designing/executing around them to be filled later. unless there is a huge blocker, then ask"). Build each item's recommended option behind one seam (a config value, an enum variant, one function) so his answer swaps that seam and nothing else. The item stays open and its file says what the build chose. Ask only when no recommended option can be built at all.
- At plan time he can sanction assumptions outright ("make initial plan, make assumptions and open items in a folder"). The assumption is not asked first; it becomes an item with a recommended option and the plan is written around it. Questions about how the thing feels to use are still asked ([[principle-01-no-assumptions]]).
- A resolved item is not archived. Fold the decision into the docs it affects, then delete the file and its index line ([[principle-56-close-out-housekeeping]]).
- The register is [[principle-57-user-docs-are-an-icd]]. Options follow [[principle-65-numbered-recommendations-get-one-word-replies]].

## anti-pattern

The same What / Issue / Decisions / table template on every item, so a one-sentence typo fills a page. Lines hard-wrapped at 100 columns, which break on a narrow screen. Open decisions buried in a plan section, or one OPEN.md holding forty items.
