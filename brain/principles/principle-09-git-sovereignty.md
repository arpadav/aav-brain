---
name: principle-09-git-sovereignty
kind: principle
tier: conditional
rule: Prepare the record, never publish it. No commits/tags/version bumps without explicit say-so. Never overwrite his manual edits.
interest: [intent-sovereignty]
confidence: very-high
evidence_count: 11
tells: ["do NOT commit", "i bump cargo tomls manually", "i will go through and verify the messages", "im the one who editted this", "files: <tree> commit: 'an example pre-filled commit'", "then i can simply say Y to accept or N to not accept the commit message"]
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
- The interaction shape he specified directly: *"i want you to say something like `files:
  <tree> commit: 'an example pre-filled commit'` where the commit descriptions are very
  short. then i can simply say Y to accept or N to not accept the commit message, and i can
  write my own."* One category at a time, a short pre-filled message, Y/N, his own words win
  when he supplies them.
- Draft **shorter** than feels sufficient - he compresses further, not less: drafted "prune
  finished plans and stale docs" became his "prune stale"; "updated skills/agents" and
  "updated principles + graph" were his own replacements, not accepted drafts. His commit
  register is terser than the draft, every time.
- For changelogs: "based off git diff ... add to changelog for 0.1.2. do NOT bump cargo
  tomls - i do that manually."
- For surgical reverts: "look at git diff and see if you can simply git reset - but if
  there are non-step2 changes then cherry pick those."

**Anti-pattern that draws heat.** Auto-committing; bumping a version; a linter/agent
reverting his hand-edited `Cargo.toml` ("im the one who editted this. whats wrong with
you? just do what youre told"). -> [[principle-15-tone-is-signal]].
