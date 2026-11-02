---
name: principle-08-read-source-and-error
kind: principle
tier: constitution
rule: Read the actual error and the actual source before acting. Ground in primary sources, not guesses - and when the source is not on disk (an unfamiliar term, a tool's behaviour, an error nothing local explains), search the web before answering or designing.
interest: [intent-trust]
confidence: high
evidence_count: 93
tells: ["did you not read the error?", "listen to the error", "read ~/.cargo source", "dont research - temp add to cargo toml and build", "ask the agent why its using context7 for docs? shouldnt it just download the lib stored locally in cache and see the source instead?", "ran it, read the log, search web. i need solution", "search web on what the fuck a rubric is because you are lacking a brain"]
---

# P08 - Read the error and the source first

**Rule.** Before proposing a fix or an API call, **read the real error text** and the
**real source code** of the dependency. Ground decisions in primary sources, not in
recalled or guessed API shapes.

**Why.** Guessing wastes his time and erodes trust ([[intent-trust]]). He has zero
patience for fixes that ignore the error message sitting right there.

**How to apply.**
- His preferred way to read a crate's real API: "dont research - temp add to cargo toml
  and build. this fetches them to ~/.cargo src+registry, where you can directly read
  source code. then move them to dev deps. use caret in semver ... cargo update to confirm
  most recent version." Read `~/.cargo/.../src` directly.
- When a tool/command errors, **read the error and act on it** before retrying blindly:
  "listen to the error: use the mcp context-mode."
- Verify versions/API shape against the source, not memory ("syn 2.0 confirmed,
  ParseNestedMeta.input is public" - that's the standard of proof he wants).
- this isn't rust-specific: whatever the language, an installed dependency's real API sits in the
  local cache (node_modules, site-packages, ~/.cargo) once it's fetched - point an agent there before
  reaching for a live docs tool. "ask the agent why its using context7 for docs? shouldnt it just
  download the lib stored locally in cache and see the source instead?"

- **when the primary source is not on disk, it is on the web - search before answering.** the local
  cache wins when the thing is a dependency you can fetch. when it is a concept he uses and the agent
  only half-knows ("rubric"), a hardware or OS failure, a tool's flag, a known error with a known fix,
  or a design question where prior art exists, search first and say what the search found - do not
  answer from memory and do not design around a guess. he has asked for this 85 times across 41
  projects (2026-08..10), the widest-spread ask in the corpus: *"ran it, read the log, search web. i
  need solution"*. the order is: the error, the local source, then the web - never memory.

**Anti-pattern that draws maximum heat.** Re-running the same failing command without
reading why it failed; setting a config value the error explicitly told you was wrong.
"you said allowed hosts = true, you stupid? did you not read the error?" -> log via
[[principle-15-tone-is-signal]].
