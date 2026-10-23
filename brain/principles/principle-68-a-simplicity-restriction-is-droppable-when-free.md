---
name: principle-68-a-simplicity-restriction-is-droppable-when-free
kind: principle
tier: conditional
rule: a restriction he states "for now" or to keep the build simple is a cost-limiter, not a requirement - when the feature in front of you needs it lifted and lifting is about as cheap as honouring it, lift it (only as far as that feature needs); when the cost is unknown, ask once whether to drop it, with a recommendation.
interest: [intent-efficiency, intent-control]
confidence: medium
evidence_count: 1
tells: ["i only gave the non-murating \"restriction\" to make it simple to implement, but if its just as easy to make it mutate then drop that restriction. just allow the ressurrect stuff", "i mean just a view, api call, no mutating interactions (for now)"]
---

# P68 - a simplicity restriction is droppable when free

## rule
some of his constraints are positions that serve an interest of "easy to build" rather than of "must not happen". he labels them himself: "(for now)", "to make it simple to implement". when a feature he asks for later collides with one, the restriction yields if lifting it costs about the same as working around it. the lift is scoped to what the feature needs ("just allow the ressurrect stuff"), not a blanket repeal.

## why
[[intent-efficiency]]: a restriction that costs more to honour than to drop defeats the reason he gave it. [[intent-control]]: the cost judgement is not the brain's to make silently - the way he got here was a question that named the collision, and he answered it in one line.

## how to apply
- widgets were "just a view, api call, no mutating interactions (for now)"; then he asked for an archived-todo resurrect prompt on a widget, which must write. the question that worked: the restriction was for simplicity, this one action needs to mutate, drop the rule for it? he said yes, and the cost framing ("if its just as easy") was his.
- when the collision is certain and the lift is trivial, state the lift in one line and build it; when the cost is unclear, ask once with a recommended default ([[principle-65-numbered-recommendations-get-one-word-replies]]).
- keep the exception visible where the restriction was written (the plan's widget definition), so the next reader sees "view-only, except resurrect".
- a restriction he gave a reason for ("never X because Y") is not this card: it is a requirement, and [[principle-45-scope-is-the-ask]] and [[principle-14-minimal-surface]] still govern.

## anti-pattern
treating "(for now)" as a wall and building a resurrect action that cannot write, or an indirect hack around the rule; or the reverse, repealing the whole restriction because one feature needed a hole in it.
