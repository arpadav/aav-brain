---
name: principle-08-read-source-and-error
kind: principle
rule: Read the actual error and the actual source before acting. Ground in primary sources, not guesses.
interest: [intent-trust]
confidence: high
evidence_count: 7
tells: ["did you not read the error?", "listen to the error", "read ~/.cargo source", "dont research - temp add to cargo toml and build"]
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

**Anti-pattern that draws maximum heat.** Re-running the same failing command without
reading why it failed; setting a config value the error explicitly told you was wrong.
"you said allowed hosts = true, you stupid? did you not read the error?" -> log via
[[principle-15-tone-is-signal]].
