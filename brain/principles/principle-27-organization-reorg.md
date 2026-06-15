---
name: principle-27-organization-reorg
kind: principle
rule: organization and folder/subfolder hierarchy are critical, always. reorg in BOTH directions by threshold: flat->tree when a file is too long or a folder has too many flat files; tree->flat when a refactor shrank things and the structure is now overkill.
interest: [intent-craft]
confidence: very-high
evidence_count: 5
tells: ["folder/subfolder hierarchy is critical", "organization is critical always", "tree-based split up", "reorg is critical in both directions", "file too long, folder too many flat files"]
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
the trigger is a threshold in either direction, not a one-time decision.

## why
the right shape keeps things findable and atomic ([[intent-craft]]). a 2000-line file and a folder of
50 flat files are both unsustainable; so is a 3-level tree wrapping two tiny files. organization is
how the codebase stays navigable as it grows AND as it shrinks.

## how to apply
- watch the thresholds both ways. after any refactor, re-ask: is anything now too big (split) or too
  small (collapse)?
- when splitting, respect existing contracts (e.g. a flat glob over `principles/*.md` keys the graph;
  subfoldering would need the glob to recurse - only do it if the win beats the contract change).
- semantic placement first: a thing belongs in the file/folder that matches what it IS
  ([[principle-26-struct-based]], the semantic-architecture lens).

## orthogonality
the big-structural-change trio, kept distinct: [[principle-20-refactors-welcome]] is the DISPOSITION
(dont dodge a change because its big); P27 is WHERE things live (the folder/file tree, flat<->tree by
threshold); [[principle-28-dry-merge-blast-radius]] is collapsing DUPLICATION specifically. attitude
vs tree-shape vs de-duplication.

## anti-pattern
letting a file grow unbounded because splitting is work; or keeping a deep tree after a refactor
hollowed it out. ignoring hierarchy because "it still runs".
