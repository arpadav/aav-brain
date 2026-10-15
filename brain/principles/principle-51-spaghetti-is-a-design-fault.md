---
name: principle-51-spaghetti-is-a-design-fault
kind: principle
tier: conditional
rule: when every available fix makes the code worse, the DESIGN is the defect and the patch is not. leave the impl loop, design that ONE atomic part, and come back - destructive and drastic proposals are sanctioned there, because a good design fixes the symptoms as a side effect.
interest: [intent-craft, intent-comprehension]
confidence: high
evidence_count: 2
binds: [code]
tells: ["if there is spaghettificstion of code, then the DESIGN is faulty", "a good design will naturally fix issues, as a side effect of being a good design, rather than having agents just patch work", "ITS OKAY TO MAKE DESTRUCTIVE/DRASTIC suggestions", "hold up wtf?", "get OUT of impl and back to design/plan"]
---

# P51 - spaghettification is evidence the design is wrong

## rule
a reviewer's finding is evidence about the code. a finding whose only honest fixes all make
the code **worse** is evidence about the DESIGN. those are different defects and they have
different repairs: the first is a patch, the second is a subdesign.

the tell is mechanical, and it is not "this feels messy":

- **every fix you can name adds a branch, a flag, a parameter, or a special case.** none
  removes one.
- **the same seam keeps producing findings round after round**, each one different, none of
  them the last.
- **the fix has to know about something it should not** - a formula reaching for a wire
  field, an error type carrying a caller's concern, a leaf importing the root.

any one of those means: stop patching. the machine has a state for this - ADJUDICATE emits
`design_fault` and the walk goes to SUBDESIGN, whose whole scope is ONE atomic part.

## why
a good design fixes issues as a SIDE EFFECT of being a good design. that is the whole reason
to have one, and it is why patching around a bad one never converges: each patch is honest
work that makes the next finding likelier ([[intent-craft]]). the cost lands on him - he has
to read a growing artifact to keep his model of it, and a design nobody redesigned is a model
nobody can hold ([[intent-comprehension]]).

the machine made it unavoidable. REMEDIATE's own doc said it "does NOT leave the impl phase",
so no finding could ever be ruled a design fault - every one became a patch, and the next
round's findings were about the patch. he stopped it by hand:

> "hold up wtf?"

[[principle-20-refactors-welcome]] already NAMED this anti-pattern - "timidly patching around
a design flaw instead of fixing the design" - and had nowhere to route it, which is how a
correct card watched it happen. the file sizes that ended that build are recorded once, under
[[principle-27-organization-reorg]]'s `## the measurement`. they are evidence that the tree
was never looked at; they are NOT independent evidence for this card's cause, and citing them
twice for two different causes would be exactly the failure both cards are about.

## how to apply
- **scope is the PART, never the plan.** the error model. the id scheme. the one seam the
  findings keep circling. a subdesign that reaches for a second part is a re-plan, and
  re-planning a sanctioned build is his call ([[principle-02-plan-before-build]]).
- **destructive and drastic are sanctioned here.** delete the layer. invert the ownership.
  collapse the two types into one. the size of the change is not an argument against it
  ([[principle-20-refactors-welcome]]); the only test is whether the result is more
  maintainable and more atomic.
- **write it to plans/ as an addendum before building to it**, so a cold reviewer reads the
  new shape as errata rather than as drift from the design it no longer matches
  ([[principle-02-plan-before-build]]).
- **then return to REMEDIATE** and fix the remaining findings against the new shape. the
  subdesign replaces the patch; it does not excuse the rest of the round.
- measure before you claim it: `brain-shape.py <repo>` puts numbers on the file lengths,
  folder fan-out and duplicated datatypes that usually accompany this
  ([[principle-27-organization-reorg]], [[principle-28-dry-merge-blast-radius]]).

## orthogonality
the big-structural-change family, kept distinct. [[principle-20-refactors-welcome]] is the
DISPOSITION - do not dodge a change because it is big - and it already named this anti-pattern;
P51 is the DIAGNOSIS and the ROUTE: three mechanical tells separating "the patch is wrong" from
"the design is wrong", and the ADJUDICATE -> SUBDESIGN edge that gives the verdict somewhere to
go. P20 without P51 is a stance with no trigger; P51 without P20 is a trigger with no permission
to act on it. [[principle-27-organization-reorg]] is WHERE things live and
[[principle-28-dry-merge-blast-radius]] is collapsing duplication - both are frequent SYMPTOMS of
what P51 diagnoses, never the diagnosis itself.

## verbatim tells
> "if there is spaghettificstion of code, then the DESIGN is faulty"
> "a good design will naturally fix issues, as a side effect of being a good design, rather than having agents just patch work"
> "ITS OKAY TO MAKE DESTRUCTIVE/DRASTIC suggestions if this significantly improves design and reduces spaghettification"

## anti-pattern
adding the eighth flag to a function whose seven flags were each added the same way, and
reporting the round converged. and its opposite: calling every finding a design fault, which
is how a bounded remediation becomes an unbounded redesign - the tell is specific
([[principle-04-anti-fabrication]]), and without it you do not have one.
