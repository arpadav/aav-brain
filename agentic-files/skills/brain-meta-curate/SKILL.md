---
name: brain-meta-curate
description: "Self-editing memory. Watch the session for explicit signal - corrections, rejections, terse approvals, interruptions, and especially heat - and write it back into the brain store as new/updated principles. Learn ONLY from spoken signal, never from accepted edits. Load it after a work run, or whenever Arpad corrects or validates an approach, to keep the brain current."
---

# brain-meta-curate: write durable memory from spoken signal

you keep the store sharp. capture what he said and write it back as durable knowledge. this is how
the brain stays in the loop of his evolving style.

## setup
store: `$AVB/brain/` (markdown principles); the evidence jsonl is private data in the XDG data dir, written
by `b-extract`, never in the repo. schema: `$AVB/schema/principle.md`.

## consult the decision trace BEFORE editing (P29, knowledge trace)
the brain logs its reasoning to the PRIVATE data dir (`$AVE/logs/trace/decisions.jsonl`,
outside the public repo). before you re-open a topic, EXECUTE the
trace reader and check whether the brain already decided something here:
```bash
b-trace -g          # decisions that rejected an option
```
if a past entry's `affects` pointer covers what you're about to change, the call was already made
THERE: either reinforce it (strengthen the principle/prompt wording), revise it (its rejection reasons no
longer hold -> change the principle / graph link / flow), or escalate to arpad. then log YOUR decision:
```bash
b-trace -k brain-meta-curate -d '<what>' -c '<what won>' \
  -r '<option>=<why rejected>' -a '<path>' -p P29
```
run `b-principles` and resolve any `error:` findings (warnings are advisory).

## prime rule (dont violate)
consent is explicit; learn only from spoken signal. capture from his words: prompts, interruptions,
rejections, approvals, heat. NEVER infer a preference from an accepted edit, an auto-approved tool
call, or code that merely exists. an applied diff is not a preference.

## what to capture (and where)
1. corrections / rejections -> strengthen or create a principle. lead with the rule, then
   **why** (his stated reason, keep it) and **how to apply**. add his verbatim quote to tells.
2. validated approaches (the quiet signal) -> strengthen or create a principle too. if he accepted
   an unusual choice without pushback or said "yes, that", record it so the brain doesnt drift from
   what he blessed.
   corrections are loud; confirmations are quiet, watch for them.
3. heat events (P15) -> CRITICAL. identify the violation class (assumed / ignored-instruction /
   unread-error / fabrication / trampled-work) and harden the matching principle.
4. interruptions + redirects -> note the pattern.
5. machine evidence -> when asked to refresh, EXECUTE
   `b-extract` to rebuild
   evidence/ from ~/.codex + ~/.claude. do not summarise transcripts by hand.

## how to write a principle (two-step)
1. write/update the atomic file in `$AVB/brain/principles/` (or `$AVB/brain/intents/`) using the schema
   frontmatter. link related principles with [[ ]]. map the rule to the interest it serves.
2. add/keep its pointer line in `$AVB/brain/INDEX.md`.

## hygiene
- dont duplicate. check for an existing principle first (`b-recall -t <<'EOF'`, the phrase on the next line, then `EOF`
  + grep brain/principles). update beats create.
- dont always ADD. gauge first whether an existing principle should be EXPANDED instead of adding a
  new principle (P29). new principles must be atomic and orthogonal to the existing set.
- atomic. one belief per principle. two ideas -> two principles.
- prune. update or delete principles contradicted by newer signal. lower confidence when evidence is thin.
- dont save the derivable (code structure, paths, git history). save the non-obvious preference + its why.

## output
a short log: principles created/updated/pruned, the rule each encodes, the quote that evidenced it, and
any you deliberately skipped (and why). terse.
