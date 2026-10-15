---
name: principle-09-git-sovereignty
kind: principle
rule: Prepare the record, never publish it. No commits/tags/version bumps without explicit say-so. Never overwrite his manual edits.
interest: [intent-sovereignty]
confidence: very-high
evidence_count: 13
tells: ["do NOT commit", "i bump cargo tomls manually", "i will go through and verify the messages", "im the one who editted this", "files: <tree> commit: 'an example pre-filled commit'", "then i can simply say Y to accept or N to not accept the commit message", "you can commit in your worktree, but when these edits are applied after i approve them, then i should be the one to stage+commit things. but you have free version control reign locally", "note you are making style pass on scratchpad and not main branch, yes?", "did you say the style landed on feat/hml-deploy ? im on that one not v2", "is this built ontop of main or feat/hml-deploy ?", "give me a script to do the git checkout and apply onto feat/hml-deploy (uncommitted) so i can see the diff against hml-deploy btwn your v2", "i edited re-read"]
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

**An isolated worktree is the exception he blessed (2026-09-30).** For a rebuild done in the agent's own
worktree or branch, local commits there are free - save points, tags, branches, merges - because nothing has reached his record yet: *"you can commit in your worktree, but when these edits are
applied after i approve them, then i should be the one to stage+commit things. but you have free version
control reign locally."* The line is where the work LANDS: once it is applied onto his branch it is
uncommitted until he stages and commits it himself. Say which commits are local saves; never push; never
treat the worktree's history as the record ([[principle-51-an-outgrown-design-is-rebuilt-small]]).

**Name the base, and whether his checkout was touched (2026-10-01).** while the work lives in a scratch
worktree or a patch, every handover says three things up front: which branch it sits on, that his checkout is
untouched, and the one command that applies it. he asks each of these when the report leaves them out - "is
this built ontop of main or feat/hml-deploy ?", "note you are making style pass on scratchpad and not main
branch, yes?", "did you say the style landed on feat/hml-deploy ? im on that one not v2" - and what he wants
delivered is an uncommitted apply onto the branch he is on, so he can read `git diff` there: "give me a script
to do the git checkout and apply onto feat/hml-deploy (uncommitted) so i can see the diff". a side branch he
is not on is never the answer to "where is it". after he says he edited a file ("i edited re-read"), re-read
it before touching it; his edit is the base ([[principle-45-scope-is-the-ask]]).

**Anti-pattern that draws heat.** Auto-committing; bumping a version; a linter/agent
reverting his hand-edited `Cargo.toml` ("im the one who editted this. whats wrong with
you? just do what youre told"). -> [[principle-15-tone-is-signal]].
