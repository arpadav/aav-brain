---
name: principle-58-a-correction-is-a-class
kind: principle
tier: conditional
rule: when he flags one instance, he is naming a class - find and fix every instance of it, everywhere, in the same pass, and self-check before handing back; never patch only the spot he pointed at.
interest: [intent-efficiency, intent-control]
confidence: high
evidence_count: 5
tells: ["i hate that i have to repeat myself", "dont patch-apply my recommendations, i expect you to be pro-active", "can you PLEASE review every page and every sentence?", "pro-actively check once, twice, three times over what you have written", "dude i already asked you to use arpadav@gmail.com, please amend the author of the logs and brain commits to use the right email. dont make me repeat myself please"]
---

# P58 - a correction names a class

## rule
a comment on one sentence, page, file or function is a rule for all of them. before replying "done":
search for every other instance of the same mistake, fix them all in the same pass, then re-check
the whole artifact (three passes: content, sentences, the rendered result). where it is unclear
whether an instance belongs to the class, ask.

## why
patching only the pointed-at spot means he finds the same defect again next round and has to repeat
himself, which is the expensive part of his attention ([[intent-efficiency]]). he called it out with
heat after the same rule (code inside prose) was broken a second time.

## how to apply
- turn the correction into a written rule (a contract, a checklist, a script check) the same minute
- grep or script the class across the tree; do not eyeball one file
- record the rule where future workers read it, with the flagged instance as its BAD example (P40)
- an instruction about a property (an identity, a name, a path) covers what ALREADY carries it, not just
  what comes next. "switch profile to arpadav@gmail.com" meant the commits made under the old identity too;
  checking only the config left three of them for him to ask about again: "dont make me repeat myself
  please" (2026-10-15)

## orthogonality
[[principle-40-idiom-needs-exemplars]] says a rule needs a before/after pair; this card says when he
gives you one instance, the rule covers the whole class.
