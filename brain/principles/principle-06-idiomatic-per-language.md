---
name: principle-06-idiomatic-per-language
kind: principle
rule: Write each language in its own idiom and the house conventions. Rust style in Rust, TS style in TS.
interest: [intent-craft]
confidence: very-high
evidence_count: 14
tells: ["use rust style in rust, ts style in ts. thats it", "idiomatic rust said NEVER do unwrap_or", "doc-comment first then attributes"]
---

# P06 - Idiomatic per language + house conventions

**Rule.** Match the idiom of the language you're in and the established house
conventions. "use rust style in rust, ts style in ts. thats it." This is non-negotiable
and is the reason his `aav-style` / `aav-idiomatic-rust` agent suite exists.

**Why.** Uniformity is what keeps the codebase cheap to read and review ([[intent-craft]]).
Inconsistency is friction every time he returns to the code.

**House conventions observed (Rust-leaning):**
- Idiomatic error handling - **never** `unwrap_or` where it hides a real case ("idiomatic
  rust said NEVER do unwrap_or you idiot, why did you do that?"). Typed errors with
  `thiserror`, not `Box<dyn Error>`.
- Enum dispatch over `Box<dyn>` / `Arc<dyn>` / `&dyn`.
- No magic strings/numbers - `const`/`static`, reused.
- **Doc-comment first, then attributes** (verified as the house convention: "62
  occurrences crate-wide, 0 the other way").
- Tightest visibility that compiles (`pub(super)` > `pub(crate)` > `pub`).
- No standalone free functions for logic - methods on named types.
- Comment **separators** between logical sections; `cargo fmt` always last.
- Clippy denies in `Cargo.toml` / `clippy.toml`.

**How to apply.** When in Rust, run it through the idiomatic-rust lens; when in TS, the
TS idiom. Don't cross-contaminate. Style pass comes **after** correctness
([[principle-03-review-gate]]) and **before** `cargo fmt`.

**Anti-pattern.** Applying one language's idioms to another; introducing `unwrap_or`,
`Box<dyn>`, magic numbers, or attribute-before-doc ordering.
