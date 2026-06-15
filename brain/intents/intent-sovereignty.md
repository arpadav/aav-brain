---
name: intent-sovereignty
kind: interest
one_line: The permanent record - commits, versions, releases, his manual edits - is his to control.
negotiation: position="dont commit / i bump versions manually / i verify the messages" -> interest="sovereignty over the durable, public, irreversible record"
---

# Interest: SOVEREIGNTY (control of the permanent record)

There is a bright line between the *working tree* (the agent may churn it freely under a
blessed plan) and the **permanent record** - commits, tags, version numbers, published
crates, anything public or hard to reverse. That record is Arpad's sovereign territory.
He decides what enters it and how it is worded.

**Positions that serve this interest:**
- "do NOT commit"
- "do NOT bump cargo tomls - i do that manually"
- "categorize them based off semantics ... make a bashscript ... then i will go through
  and verify the messages and run the bash script"
- "git change upstream origin ... checkout appropriately named branch, do NOT commit"
- "the bench.jpg should be included in the repo, but it shouldnt be included in the library"

**The interest behind them:** what is committed/published is irreversible and carries his
name. He wants every entry semantic, reviewable, and *personally approved*. He is happy
to let the agent **prepare** the record (stage, draft semantic messages, write the script)
but reserves the **act of recording** for himself.

**How to satisfy it:** prepare, never publish. Draft commits as a script or message he
runs; categorize changes by semantics; surface what would be committed; stop at the line.
Treat his manual edits as immutable unless he says otherwise. See [[principle-09-git-sovereignty]].
