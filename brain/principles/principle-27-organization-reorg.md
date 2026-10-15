---
name: principle-27-organization-reorg
kind: principle
tier: narrow
rule: organization and folder/subfolder hierarchy are critical, always. reorg in BOTH directions by a MEASURED threshold, never an adjective: the numbers live in shape.toml and brain-shape.py reports the crossings - flat->tree past file_lines or folder_files, tree->flat when a refactor shrank things and the structure is now overkill.
interest: [intent-craft]
confidence: very-high
evidence_count: 5
tells: ["folder/subfolder hierarchy is critical", "organization is critical always", "tree-based split up", "reorg is critical in both directions", "file too long, folder too many flat files", "i dont want 5 files all talk about design when it can be one file", "living docs with explicit design decisions i made never to be deleted unless design changes again"]
---

# P27 - organization and bidirectional reorg

## rule
hierarchy is not an afterthought, its critical and constant. and reorg goes BOTH ways, driven by a
size/cohesion threshold:
- flat -> tree: a file got too long, or a folder has too many flat files -> split into a subtree
  (modules, subfolders) so each piece is atomic and findable.
- tree -> flat: a refactor removed/moved a lot of content, so some files/folders are now too small
  and the tree is overkill -> collapse it back to flat. structure for its own sake is debt
  ([[principle-14-minimal-surface]]).
the trigger is a threshold in either direction, not a one-time decision - and the threshold is a
NUMBER, read from `shape.toml` and reported by `brain-shape.py`, because "too long" is an adjective
and a worker resolves an adjective against its own priors ([[principle-40-idiom-needs-exemplars]]).
**the values live in `shape.toml` and are not repeated here** - a number written down in two places
is a number that will disagree with itself.

a crossing is a FINDING, not a verdict. a 2400-line file that is one coherent table of sourced
constants is fine and nothing here may split it; the number says look, the judgement is still
yours.

## why
the right shape keeps things findable and atomic ([[intent-craft]]). a 2000-line file and a folder of
50 flat files are both unsustainable; so is a 3-level tree wrapping two tiny files. organization is
how the codebase stays navigable as it grows AND as it shrinks.

## the measurement
this is the single statement of the evidence behind the numbers. every other file that needs it
cites this section rather than retelling it - one anecdote retold in nine places drifts in nine
directions, and the first draft of that retelling had already produced "five straight phases" in
one copy against "phases 5 through 8" in another.

corpus: the four claude sessions of the budget build, 2026-08-28 to 2026-09-05, under
`~/.claude/projects/-home-arpad-repos--sandbox-budget/`. it is LIVE and it EXPIRES, so these are
figures as of 2026-09-05 and re-running the count will move them.

- **95% of review dispatches were scoped to a diff.** 74 of 78 dispatches to a reviewing lens named
  a diff or a git range as the thing to read.
- **`finance/src/ledger.rs` went from 5 lines to 7540.** it passed 2000 at task 2.3 and then
  cleared **twelve** gate and style-pass commits without one of them naming its length. its peers
  ended at 6403 (`tax.rs`) and 5885 (`fire.rs`).
- **the layout lens stopped being dispatched.** `aav-idiomatic-rust-organization` ran at phases 1-4
  and was not dispatched AT ALL for phases 5, 6, 7, 7b and 8.
- **but the architecture lens DID run at every one of those phases** - on the diff, asked for design
  conformance. the design document says nothing about file length, so conformance passed. **that is
  the finding.** it is not that nobody looked; it is that what they were shown could not contain the
  defect.
- **this card was in context for it.** it appears in 9 recall outputs across the same build.
- **~29% of agent dispatches were refused** by the permission classifier (55 of 187), between 14%
  and 50% depending on the agent, and a refusal was absorbed silently rather than reported as a hole.

what is NOT claimed, because it was measured and did not hold: that no reviewer ever read the whole
crate, and that the layout lens was dropped because it was denied. the denials were retried and the
retries carried; the lens then stopped being asked for, which is a different failure.

## how to apply
- **run `brain-shape.py <repo>` at every phase gate**, and hand its crossings to the structure lens
  as that lens's input. this is the half a diff-scoped review cannot see: a phase that adds 800
  lines to a 6700-line file produces a hunk that reads fine, and the FILE is the defect
  ([[principle-19-think-in-code-ops]]).
- watch the thresholds both ways. after any refactor, re-ask: is anything now too big (split) or too
  small (collapse)?
- when splitting, respect existing contracts (e.g. a flat glob over `principles/*.md` keys the graph;
  subfoldering would need the glob to recurse - only do it if the win beats the contract change).
- semantic placement first: a thing belongs in the file/folder that matches what it IS
  ([[principle-26-struct-based]], the semantic-architecture lens).

## plans and design docs
merge overlapping plan/design docs into one living file; explicit decisions he made are never deleted unless the design itself changes again. purge outdated items, keep his wording.

## orthogonality
the big-structural-change trio, kept distinct: [[principle-20-refactors-welcome]] is the DISPOSITION
(dont dodge a change because its big); P27 is WHERE things live (the folder/file tree, flat<->tree by
threshold); [[principle-28-dry-merge-blast-radius]] is collapsing DUPLICATION specifically. attitude
vs tree-shape vs de-duplication.

## anti-pattern
letting a file grow unbounded because splitting is work; or keeping a deep tree after a refactor
hollowed it out. ignoring hierarchy because "it still runs".

and the one that actually happened, which is worse because it looks like compliance: this card was
in context (`## the measurement`) while a file grew to 7540 lines, because every review was scoped to
a diff and nobody ever ran `wc -l`. **a card that is loaded and never measured against is a card that
did not fire** ([[principle-40-idiom-needs-exemplars]], [[principle-51-spaghetti-is-a-design-fault]]).
