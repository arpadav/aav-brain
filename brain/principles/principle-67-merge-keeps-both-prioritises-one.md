---
name: principle-67-merge-keeps-both-prioritises-one
kind: principle
tier: conditional
rule: when consolidating two machines' diverged work, where both built a real mechanism for the same job, keep both with a stated priority and let the redundant one be pruned later on evidence - do not pick a winner and delete the loser in the merge. a merge ends with everything on main.
interest: [intent-sovereignty, intent-craft]
confidence: medium
evidence_count: 1
binds: [git, brain]
tells: ["id like to keep both, but prioritize c1? and if c2 was redudant then it can be pruned/removed later", "i want all merged stuff to be on main at the end", "push computer-2 where it encompasses computer-1 changes, and prune computer-1", "i trust your merge"]
---

# P67 - merge: keep both, prioritise one, prune later

## rule
on a c1/c2 style consolidation, genuine duplicates of the SAME rule fold into one card (he took "fold into one card each"). but two working MECHANISMS for one job (brain-gate vs brain-shape) are not folded on a guess: keep both, name the priority, and mark the loser for later removal once use shows it is redundant. the finished merge lands on main in every repo (logs -> brain -> home), and the spent branch is pruned.

## why
deleting a mechanism he has not seen fail is irreversible in a merge; deferring is cheap and the pruning is evidence-driven ([[principle-28-dry-merge-blast-radius]] still holds for true duplicates; this is for mechanisms with different triggers). one run, so low confidence. he trusts the resolution itself ("i trust your merge") but keeps the commit ([[principle-09-git-sovereignty]]).

## how to apply
- ask per divergent mechanism with options; put the fold/renumber default first as Recommended ([[principle-65-numbered-recommendations-get-one-word-replies]]).
- when he keeps both, record which is primary where the next reader will see it, and a note on what would make the other removable.
- merge order is leaves first: logs repo, then brain (pointing at merged logs main), then home; finish with all on main, stage only.
