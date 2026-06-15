---
name: principle-13-performance-obsession
kind: principle
rule: Pursue the fastest correct path; measure honestly with criterion; care about raw speedups and % deltas.
interest: [intent-craft, intent-trust]
confidence: high
evidence_count: 9
tells: ["make our single u32 faster", "best/fastest of each api", "raw speedups or slowdowns and raw % comparison", "trait-wise dispatch"]
---

# P13 - Performance is a feature

**Rule.** For systems/library code, the fastest *correct* implementation is the goal.
Measure with `criterion`. Care about **raw speedups/slowdowns and % deltas**, not vanity
units. Prefer zero-cost abstractions: trait-based static dispatch, SIMD, compile-time
`cfg`-gating over runtime checks.

**Why.** This is his craft and his market ([[intent-craft]]); and the speedups must be
*real* and honestly measured ([[intent-trust]], see [[principle-04-anti-fabrication]]).

**How to apply.**
- Read the dependency source to use its fastest API: "read the itoa api under ~/.cargo
  for the source code to ensure we are using the best/fastest ... (Buffer::new() is this
  the only way or are there multi-speedups?)."
- Prefer trait dispatch over a `default` match arm: "make it a trait instead and impl for
  each precision ... trait-wise dispatch. then you can pub(crate) the fmt_u* and only pub
  fmt expose."
- Compile-time gate SIMD, don't runtime-check it: "remove the is x86 cache check ... we
  already compile time cfg gated it."
- Benchmarks must isolate the thing measured: time the write into an existing buffer, not
  the allocation; don't merge `write!` and `writeln!` legends.

**Anti-pattern.** Runtime feature checks that were already `cfg`-gated; a `default` arm
where a trait impl belongs; benchmark legends that conflate distinct operations.
