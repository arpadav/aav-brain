---
name: principle-28-dry-merge-blast-radius
kind: principle
rule: merge DRY-violating structs/files even when it touches many files and peripherals. do NOT be dissuaded by a large amount of work. keep things separate ONLY for a real reason beyond programming laziness; otherwise ALWAYS change it.
interest: [intent-craft]
confidence: very-high
evidence_count: 4
tells: ["2 structs ... identical purposes ... i want to merge", "touches many more files and peripherals", "do NOT be dissuaded by a large amount of work", "real reason BESIDES programming laziness", "it should ALWAYS be changed"]
---

# P28 - DRY-merge despite blast radius

## rule
when two structs/types/files serve the same purpose, merge them - even when it turns out to be more
complicated than expected because it touches many more files and peripherals. the blast radius is not
a reason to stop. the ONLY reason to leave duplicates separate is a real, stated, technical reason;
"its a lot of work" / laziness is never that reason. if the only thing keeping them apart is effort,
ALWAYS change it.

## why
duplication compounds ([[intent-craft]], [[principle-05-reuse-first]]). a merge that touches 20 files
once is cheaper than two diverging copies maintained forever. large refactors are welcome when they
improve structure ([[principle-20-refactors-welcome]]). the work is the point, not the deterrent.

## how to apply
- find a duplicate purpose -> trace the full blast radius (every file/peripheral that touches either
  side) and merge across all of them. the relevant set EXPANDS as you find dependents
  ([[principle-29-interrogate-the-work]]) - follow it.
- before merging, ask honestly: is there a REAL reason they should stay separate (different invariants,
  different lifetimes, a genuine abstraction boundary)? if yes, keep separate and note why. if the only
  reason is "merging is annoying", merge.
- this is the counterweight to "dont force churn" ([[principle-05-reuse-first]]): real duplication is
  not churn to remove; it is debt to pay.

## orthogonality
the DRY trio, kept distinct: [[principle-05-reuse-first]] is reuse BEFORE you write (dont author a
fresh copy of something that exists); P28 is REMEDIATING duplication already in the tree (merge it
despite the blast radius); [[principle-31-libraryfy-shared]] is the standing PATTERN that 2+ uses of
a datatype/helper live in one shared library. pre-write vs remediate vs standing-rule.

## anti-pattern
leaving two identical-purpose structs because unifying them touches many files. inventing a fake
"they're conceptually different" reason to dodge the work.
