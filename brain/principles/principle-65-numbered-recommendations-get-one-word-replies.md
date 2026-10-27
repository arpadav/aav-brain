---
name: principle-65-numbered-recommendations-get-one-word-replies
kind: principle
tier: conditional
rule: put findings/decisions to him as a numbered list, each with a recommended default, so he can reply "affirm" or overrule by number. his overrules are usually about keeping extensibility structure or making a value configurable.
interest: [intent-efficiency, intent-comprehension]
confidence: medium
evidence_count: 4
tells: ["1. affirm 2. affirm 3. no, this structure is fine in case more services are added 4. affirm 5. affirm 6. affirm 7. affirm 8. make this configurable.", "phase/stage in brain and in plan?", "i trust your merge", "picked the (Recommended) option on 6 of 7 merge/refactor questions: fold into one card each; one step, both triggers; by job, 3 folders; verifier runs it", "overrule: id like to keep both, but prioritize c1", "all 3: its a label, it holds sub-todos, and the label itself never gets autoscheduled just the subtasks in some causal order", "both, its free time, a man needs to recharge", "either, set it like anything else, i need X percent of time off to recharge, how its blocked is up to you", "i set how often, and i can dismiss, view next, etc"]
---

# P65 - numbered recommendations, one-word replies

## rule
each item carries your recommendation; "affirm" means take it. he rejects a finding by number with a short reason ("this structure is fine in case more services are added") or turns a hardcode into config ("make this configurable"). do not re-litigate affirmed items.

## why
he answers 8 items in one line; the format spares him context he does not hold ([[principle-49-his-interactive-app-shape]], [[principle-43-report-state-not-changelog]]). one run only, so confidence is low; the "structure for more services" overrule is a single instance, not a rule against cutting speculative structure ([[principle-51-spaghetti-is-a-design-fault]] still governs).

## how to apply
- in option menus mark the default "(Recommended)". he took it on 4 of 10 questions in one homepage run (pinned = fixed time; list first; own phone tile layout; academic page) and answered the other 6 in his own words, all of them about what his todos and his day mean: "all 3", "both", "either", "i set how often", a refit-on-any-change rule, and dropping a restriction. his hybrids come back as a superset of the options, so make options combinable (multi-select) rather than exclusive, and when the topic is his time, habits or rhythms, leave room for a free-text answer ([[principle-67-merge-keeps-both-prioritises-one]]).
- a knob that fires on its own (a resurrect prompt, a reminder) is his to set: offer "i set how often, and i can dismiss / view next" rather than a system-chosen cadence.
- keep items independent and numbered; recommendation first, reason in a clause.
- clarify terms he asks about (he asked what "phase/stage" meant in brain vs plan): define in one line, no tour.
