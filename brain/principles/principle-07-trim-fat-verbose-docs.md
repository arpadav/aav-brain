---
name: principle-07-trim-fat-verbose-docs
kind: principle
rule: Cut ancillary/YAGNI inline comments and dead surface; keep doc comments and doc tests verbose and thorough.
interest: [intent-craft]
confidence: high
evidence_count: 6
tells: ["trim the fat", "get to the damn point", "verbose doc comments tho", "remove old/deprecated/YAGNI comments which are ANCILLARY", "line by line"]
---

# P07 - Trim the fat, but keep docs verbose

**Rule.** Two opposite knobs, applied deliberately:
- **Inline comments / surface area -> minimal.** Remove old, deprecated, YAGNI, and
  ancillary comments. Go **line by line**. Get to the point. Delete dead/old test files.
- **Doc comments + doc tests -> verbose and thorough.** These are the durable interface
  and stay rich.

**Why.** Signal-to-noise ([[intent-craft]]). Inline chatter is debt that rots; doc
comments are the contract a future reader (including him) relies on. The distinction is
sharp and intentional - do not flatten both to "some comments."

**How to apply.**
- "go LINE BY LINE and remove old/deprecated/YAGNI comments which are ANCILLARY: get to
  the damn point quick and concise. verbose doc comments tho."
- Introduce **readable comment separators** between logical sections.
- Order: trim -> ensure styling -> `cargo fmt` at the very end.
- Respect the limit: "if no net reduction possible, dont force it" - no churn for its own
  sake ([[principle-05-reuse-first]]).

**Anti-pattern.** Stripping doc comments to "reduce lines"; leaving YAGNI/`// TODO old`
chatter inline; manufacturing a diff just to claim a reduction.
