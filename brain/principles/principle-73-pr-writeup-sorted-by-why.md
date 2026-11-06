---
name: principle-73-pr-writeup-sorted-by-why
kind: principle
tier: conditional
rule: when a change has grown and he wants to see the diff, write plans/PR.md that sorts the diff by WHY it exists (core ask / needed to make it work / added by review), with the files per row, so he can cut by category. a status report on a grown change has the same shape and ends in a choice: finish or cut back.
interest: [intent-comprehension, intent-control]
confidence: medium
evidence_count: 1
tells: ["list out all this into a plans/PR.md so i can see the actual diff like this. this is great, thank you", "i need a full status update. is this done yet?"]
---

# P73 - the diff grouped by why

**Why.** he judges proportion by seeing which part is the ask and which is accretion ([[principle-14-minimal-surface]]). text only; no PR is opened ([[principle-09-git-sovereignty]]).
