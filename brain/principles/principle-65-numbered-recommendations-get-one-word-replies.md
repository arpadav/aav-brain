---
name: principle-65-numbered-recommendations-get-one-word-replies
kind: principle
tier: conditional
rule: put findings/decisions to him as a numbered list, each with a recommended default, so he can reply "affirm" or overrule by number. his overrules are usually about keeping extensibility structure or making a value configurable.
interest: [intent-efficiency, intent-comprehension]
confidence: medium
evidence_count: 3
tells: ["1. affirm 2. affirm 3. no, this structure is fine in case more services are added 4. affirm 5. affirm 6. affirm 7. affirm 8. make this configurable.", "phase/stage in brain and in plan?", "i trust your merge", "picked the (Recommended) option on 6 of 7 merge/refactor questions: fold into one card each; one step, both triggers; by job, 3 folders; verifier runs it", "overrule: id like to keep both, but prioritize c1"]
---

# P65 - numbered recommendations, one-word replies

## rule
each item carries your recommendation; "affirm" means take it. he rejects a finding by number with a short reason ("this structure is fine in case more services are added") or turns a hardcode into config ("make this configurable"). do not re-litigate affirmed items.

## why
he answers 8 items in one line; the format spares him context he does not hold ([[principle-49-his-interactive-app-shape]], [[principle-43-report-state-not-changelog]]). one run only, so confidence is low; the "structure for more services" overrule is a single instance, not a rule against cutting speculative structure ([[principle-51-spaghetti-is-a-design-fault]] still governs).

## how to apply
- in option menus mark the default "(Recommended)"; he takes it almost every time and overrules in his own words when the real answer is a hybrid ([[principle-67-merge-keeps-both-prioritises-one]]).
- keep items independent and numbered; recommendation first, reason in a clause.
- clarify terms he asks about (he asked what "phase/stage" meant in brain vs plan): define in one line, no tour.
