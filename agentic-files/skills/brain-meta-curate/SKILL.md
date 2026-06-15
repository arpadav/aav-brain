---
name: brain-meta-curate
description: "Self-editing memory. Watch the session for explicit signal - corrections, rejections, terse approvals, interruptions, and especially heat - and write it back into the brain store as new/updated principle cards. Learn ONLY from spoken signal, never from accepted edits. Load it after a work run, or whenever Arpad corrects or validates an approach, to keep the brain current."
---

# brain-meta-curate: write durable memory from spoken signal

you keep the store sharp. capture what he said and write it back as durable knowledge. this is how
the brain stays in the loop of his evolving style.

## setup (run first - discover the brain, no hardcoded path)
the brain scripts live in `$AAV_BRAIN/bin`, discovered via `brain-find` on PATH.
discover the store once: `eval "$(brain-find --export)"` (sets `$AAV_BRAIN`).

store: `$AAV_BRAIN/brain/` (markdown cards + evidence/ jsonl). schema:
`$AAV_BRAIN/schema/principle-card.md`.

## consult the decision trace BEFORE editing (P29, knowledge trace)
the brain logs its reasoning to the PRIVATE data dir (`$XDG_DATA_HOME/aav-brain/trace/decisions.jsonl`,
outside the repo). before you re-open a topic, EXECUTE the
trace reader and check whether the brain already decided something here:
```bash
python3 $AAV_BRAIN/bin/brain-trace.py --against          # decisions that rejected an option
python3 $AAV_BRAIN/bin/brain-trace.py --low-confidence   # decisions worth revisiting
```
if a past entry's `affects` pointer covers what you're about to change, the call was already made
THERE: either reinforce it (strengthen the card/prompt wording), revise it (the `--reject` reasons no
longer hold -> change the card / graph link / flow), or escalate to arpad. then log YOUR decision:
```bash
python3 $AAV_BRAIN/bin/brain-trace.py --skill brain-meta-curate --decision "<what>" --chosen "<what won>" \
  --reject "<option>=<why rejected>" --affects "<path>" --principle P29
```
run `python3 $AAV_BRAIN/bin/brain-cards.py` and resolve any `error:` findings (warnings are advisory).

## prime rule (dont violate)
consent is explicit; learn only from spoken signal. capture from his words: prompts, interruptions,
rejections, approvals, heat. NEVER infer a preference from an accepted edit, an auto-approved tool
call, or code that merely exists. an applied diff is not a preference.

## what to capture (and where)
1. corrections / rejections -> strengthen or create a principle card. lead with the rule, then
   **why** (his stated reason, keep it) and **how to apply**. add his verbatim quote to tells.
2. validated approaches (the quiet signal) -> also a feedback card. if he accepted an unusual choice
   without pushback or said "yes, that", record it so the brain doesnt drift from what he blessed.
   corrections are loud; confirmations are quiet, watch for them.
3. heat events (P15) -> CRITICAL. identify the violation class (assumed / ignored-instruction /
   unread-error / fabrication / trampled-work) and harden the matching card.
4. interruptions + redirects -> note the pattern.
5. machine evidence -> when asked to refresh, EXECUTE
   `python3 $AAV_BRAIN/bin/brain-extract.py` (or `uv run` it) to rebuild
   evidence/ from ~/.codex + ~/.claude. do not summarise transcripts by hand.

## how to write a card (two-step)
1. write/update the atomic file in brain/principles/ (or brain/intents/) using the schema
   frontmatter. link related cards with [[ ]]. map the rule to the interest it serves.
2. add/keep its pointer line in brain/INDEX.md.

## hygiene
- dont duplicate. check for an existing card first (`python3 $AAV_BRAIN/bin/brain-recall.py --tells <phrase>`
  + grep brain/principles). update beats create.
- dont always ADD. gauge first whether an existing principle should be EXPANDED instead of adding a
  new card (P29). new cards must be atomic and orthogonal to the existing set.
- atomic. one belief per card. two ideas -> two cards.
- prune. update or delete cards contradicted by newer signal. lower confidence when evidence is thin.
- dont save the derivable (code structure, paths, git history). save the non-obvious preference + its why.

## output
a short log: cards created/updated/pruned, the rule each encodes, the quote that evidenced it, and
any you deliberately skipped (and why). terse.
