---
name: principle-31-libraryfy-shared
kind: principle
rule: library-fy shared datatypes and helpers. when 2+ scripts/modules use the same struct, constant, or helper, extract ONE shared library they import - never redefine the same datatype in multiple places. minimal-surface does NOT justify a duplicated struct; a shared lib IS the minimal surface.
interest: [intent-craft]
confidence: very-high
evidence_count: 5
binds: [code]
tells: ["it needs to be library-fied", "scripts help one another by sharing datatypes and common structs", "isnt general purpose or atomic enough", "node and graph representations elsewhere", "the whole point is that each approach is completely standalone", "why is this repo organization a fucking mess"]
---

# P31 - library-fy shared datatypes and helpers

## rule
scripts in a project share a library; they do not each re-define the same things. when a datatype
(a struct/class), a constant, or a helper is used by 2+ scripts, extract it into ONE shared module
that they import. one definition, written by one tool and read by another (e.g. graph writes
Node.to_dict, recall reads Node.from_dict). this is what makes the tooling general-purpose and atomic.

P14 (minimal surface) does NOT override this: a shared library IS the minimal surface - duplicating
a struct across files is MORE surface, not less. and "it's in two repos / it's a bit of work" is the
laziness P28 forbids, not a real reason to duplicate.

## why
duplicated datatypes drift and lie ([[intent-craft]]). two "Node" definitions are two things that
must be kept in sync by hand. a library is the single source of truth for a struct, the same way the
graph is the single source for served_by. reuse ([[principle-05-reuse-first]]) and DRY-merge
([[principle-28-dry-merge-blast-radius]]) demand it.

## the exception: when N independent readables ARE the deliverable

P31 is about code that HAPPENS to be duplicated. it does not apply when the artifact's whole
purpose is N independently-readable implementations of the same thing - a suite of optimisation
variants, a set of teaching examples, seven kernels that exist to be compared. there, extracting
the shared parts makes every variant unreadable on its own and couples experiments that exist to be
varied independently. the duplication IS the deliverable.

he stated this directly, with heat, after the brain built a shared `common/` for a seven-variant
CUDA suite: *"why are there common code for geometry interp and all? the whole point is that each
approach is completely standalone"*, *"i literally wrote polar formatting into ONE file in python
back in my day"*, *"why is this repo organization a fucking mess??"*.

the test is not "is this duplicated" but **"is a reader meant to open one file and have the whole
thing?"** if yes, duplicate and say so in the file. if no, library-fy.

and note the failure mode is recursive: the brain re-derived the shared-library instinct a second
time from P31 itself. a suite like this needs the anti-rule written into ITS OWN plan, in the
layout section, so the instinct is met and refused at the point it fires.

## how to apply
- FIRST ask whether N-independently-readable is the deliverable (see the exception above). if it is,
  duplication is correct and "factor this out" is an INVALID review finding to be rejected and logged.
- otherwise: if the SAME struct/helper/constant appears in 2+ files, that is a finding - propose
  the shared library and the imports. do NOT wave it away with "minimal surface" or "cross-repo".
- a build/check/load PATTERN repeated across builders -> a shared base class (e.g. an Artifact base
  holding the drift-gate), each builder supplying only what differs.
- keep genuinely-distinct types distinct (Node=knowledge vs State=sequence are different concepts,
  P30) - library-fy the SHARED ones, do not force unrelated ones into one generic type.

## anti-pattern (and where the brain failed)
defining Node/Edge in one script and a second node representation in another. the brain's own review
once argued AGAINST a shared brainlib (over-weighting P14 / using "two repos" as an excuse) - that was
wrong. when a review lens sees a duplicated datatype, it must default to library-fy, never to "leave
separate". this card exists so the brain catches it next time.
