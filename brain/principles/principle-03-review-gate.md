---
name: principle-03-review-gate
kind: principle
rule: Gate every phase with a cold, independent, multi-lens review. Converge feedback. Fix even a single-agent nit before advancing.
interest: [intent-trust, intent-craft]
confidence: very-high
evidence_count: 25
tells: ["triple review first", "COLD/UNGUIDED", "even smallest nits", "dont skimp out because youre lazy", "find ANY remaining issues or nits or large bugs"]
---

# P03 - Review-gate every phase (cold, independent, converged)

**Rule.** Between phases, run an independent review. His exact protocol:
1. Review the **git diff between phases COLD / UNGUIDED** - prompt reviewers with no
   leading context: *"check git diff btwn X and Y and surface as many issues as you have,
   biggest bugs to smallest nits, be thorough."*
2. **Converge** the feedback across reviewers. Even a nit raised by **only one** reviewer
   gets fixed before the next phase.
3. **Dispatch only the reviewers that are relevant - but never skimp.** "you dont need to
   dispatch ALL ... JUST what you think is necessary. however, dont skimp out on it
   because youre lazy, it must be thorough."

**Why.** He does not trust a single confident pass ([[intent-trust]]); independent
adversarial review is how correctness and architectural integrity get verified ([[intent-craft]]).
The "dispatch X reviewer" position is really the interest *"verify this independently so I
can trust it without reading every line."*

**How to apply.**
- Cold prompts. Don't tell the reviewer what you think is wrong - let it find it.
- The first feedback pass may be remediated by a worker; then re-review.
- "do the triple review first, then fix, then the fmt and style" - order matters:
  correctness/architecture review -> fix -> style/fmt last.
- Reviewers must not **invent** issues ([[principle-04-anti-fabrication]]): "remember not
  to make up issues, but also be heavily scrutinizing line by line."

**Anti-pattern.** Skipping the gate, a warm/guided review that only confirms your own
work, or dropping a single-reviewer nit because "it's minor."
