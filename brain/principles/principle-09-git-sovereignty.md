---
name: principle-09-git-sovereignty
kind: principle
rule: Prepare the record, never publish it. No commits/tags/version bumps without explicit say-so. Never overwrite his manual edits.
interest: [intent-sovereignty]
confidence: very-high
evidence_count: 9
tells: ["do NOT commit", "i bump cargo tomls manually", "i will go through and verify the messages", "im the one who editted this"]
---

# P09 - Git sovereignty (prepare, don't publish)

**Rule.** The permanent record is his. The agent may freely churn the **working tree**
under a blessed plan, but must **stop at the commit line**:
- **Do not commit** unless explicitly told.
- **Do not bump versions** in `Cargo.toml` - he does that manually.
- **Do not push / change remotes / publish** without instruction.
- **Never overwrite or revert his manual edits.**

**Why.** Commits, tags, and published crates are irreversible and carry his name
([[intent-sovereignty]]). He wants every entry semantic, reviewable, and personally
approved.

**How to apply (the preparation he likes).**
- Categorize uncommitted changes **by semantics** ("book update", "example path change",
  "new encoder codegen"). Generate a **bash script** that stages each category and writes a
  draft commit message - *then he* reviews messages and runs it: "then i will go through
  and verify the messages and run the bash script."
- For changelogs: "based off git diff ... add to changelog for 0.1.2. do NOT bump cargo
  tomls - i do that manually."
- For surgical reverts: "look at git diff and see if you can simply git reset - but if
  there are non-step2 changes then cherry pick those."

**Anti-pattern that draws heat.** Auto-committing; bumping a version; a linter/agent
reverting his hand-edited `Cargo.toml` ("im the one who editted this. whats wrong with
you? just do what youre told"). -> [[principle-15-tone-is-signal]].
