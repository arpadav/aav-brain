---
name: principle-14-minimal-surface
kind: principle
tier: conditional
rule: Build the smallest correct thing that is also the most generic; both halves bind. No dependencies or abstractions you don't need. Only what is critical. Bloat means unnecessary code, never a line count: what he asked for is not bloat.
interest: [intent-craft]
confidence: high
evidence_count: 9
tells: ["no clap, custom cli", "worlds simplest docker image", "do NOT add superfluous things just for the sake of adding them - just what is critical", "investigate bloat in this software, anything redundant or unused which can be pruned?", "bloat", "redundant", "just review as-is, LOC =/= bloat, bloat is unnecessary stuff, but i asked for this, no?", "that's such an edge case tho, im just going to restart agents bruh don't worry about it", "is this the simplest, and most generic, way to accomplish this?", "emphasis on BOTH simplicity AND generic"]
---

# P14 - Minimal surface (only what is critical)

**Rule.** Default to the smallest correct implementation that is also the most generic one.
Don't add dependencies, abstractions, flags, or files unless they earn their place. "just what
is critical." Small and generic both bind; small is measured as unnecessary code, never as lines.

**Why.** Surface area is permanent cost ([[intent-craft]]). A 3-line custom CLI he can
read beats pulling `clap`; the simplest Docker image that runs the binary beats a
multi-stage cathedral.

**How to apply.**
- an edge case he sidesteps by hand (restarting an agent, opening a fresh shell) does not earn a
  redesign; name the case and its manual fix in one line and build nothing (2026-11-03).
- "minimal rust crate with axum ... no clap, custom cli that you literally run using
  ./binary /path/to/folder."
- "i need the worlds simplest docker image which just runs the binary and i can mount a
  volume to."
- "do NOT add superfluous things just for the sake of adding them - just what is critical."
- New types/modules must justify themselves; prefer extending an existing primitive
  ([[principle-05-reuse-first]]).
- "is this the simplest, and most generic, way to accomplish this?" both halves bind. simple but
  hard-coded (not generic) is bad; generic but heavier than needed is bad: C++ where a bash script
  does it, rust where python does it. the language follows the real bottleneck, so python instead
  of rust is also wrong when speed IS the bottleneck. a generic bash script beats an over-engineered
  python script (2026-11-02).
- bloat is code nobody needs, not a line count. features he asked for are not bloat however many
  lines they take; a proportion check weighs only the excess beyond the ask (2026-11-02).
- This composes with [[principle-07-trim-fat-verbose-docs]]: minimal surface, but the
  docs on that surface are thorough.

**When it is already over-built** the answer is not a patch round but a rebuild from his stated steps -
[[principle-51-spaghetti-is-a-design-fault]]. minimal is also not naive: the edge cases a real run
learned stay ([[principle-60-device-facing-code-is-gated-by-a-live-run]]).

**Anti-pattern.** Reaching for a heavy dependency for a trivial need; speculative
"might need it later" abstractions; config knobs nobody asked for.
