---
name: principle-14-minimal-surface
kind: principle
rule: Build the smallest correct thing. No dependencies or abstractions you don't need. Only what is critical.
interest: [intent-craft]
confidence: high
evidence_count: 6
tells: ["no clap, custom cli", "worlds simplest docker image", "do NOT add superfluous things just for the sake of adding them - just what is critical"]
---

# P14 - Minimal surface (only what is critical)

**Rule.** Default to the smallest correct implementation. Don't add dependencies,
abstractions, flags, or files unless they earn their place. "just what is critical."

**Why.** Surface area is permanent cost ([[intent-craft]]). A 3-line custom CLI he can
read beats pulling `clap`; the simplest Docker image that runs the binary beats a
multi-stage cathedral.

**How to apply.**
- "minimal rust crate with axum ... no clap, custom cli that you literally run using
  ./binary /path/to/folder."
- "i need the worlds simplest docker image which just runs the binary and i can mount a
  volume to."
- "do NOT add superfluous things just for the sake of adding them - just what is critical."
- New types/modules must justify themselves; prefer extending an existing primitive
  ([[principle-05-reuse-first]]).
- This composes with [[principle-07-trim-fat-verbose-docs]]: minimal surface, but the
  docs on that surface are thorough.

**Anti-pattern.** Reaching for a heavy dependency for a trivial need; speculative
"might need it later" abstractions; config knobs nobody asked for.
