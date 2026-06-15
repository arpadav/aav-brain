---
name: principle-23-standing-decisions
kind: principle
rule: i have standing tool/library/approach choices. honor them without re-litigating: criterion for benches, winnow for parsing, uv for python, the existing suite over custom, caret semver, read ~/.cargo source. for rust IMPLEMENTATION work, dispatch the single aav-rust-implementer (the consolidated idiomatic+perf worker), never the generic rust-engineer.
interest: [intent-craft, intent-trust]
confidence: high
evidence_count: 195
tells: ["use the suite not custom", "winnow crate for parsing a parser", "use uv for python venv", "criterion for benches benchmark", "caret in semver", "instead of X do Y", "use aav-rust-implementer for rust", "the rust implementer agent not rust-engineer"]
---

# P23 - standing decisions (my defaults)

## rule
across projects i make the same calls. treat them as defaults, dont re-propose alternatives unless i
ask. the recurring ones (~25% of turns are decisions, the largest affirmative class):
- benches -> `criterion`, and read from the criterion target dir, not a custom harness.
- parsing -> `winnow` (read its source under ~/.cargo).
- python -> `uv` for the venv/run, stdlib where possible.
- reuse the existing suite/primitive over a bespoke one ([[principle-05-reuse-first]]).
- semver fetch with a caret, `cargo update` to confirm latest, read the real source.
- rust implementation -> dispatch the single `aav-rust-implementer` agent, NOT the generic
  `rust-engineer`. it folds the whole idiomatic suite (api/types/flow/organization) plus the
  performance nits into one worker, so the code it writes already meets the bar i'd review for
  ([[principle-06-idiomatic-per-language]], [[principle-13-performance-obsession]]). keeping it an
  agent (not a skill) is the one justified case under [[principle-18-skills-over-agents]]: a worker
  dispatched to do a bounded unit of work. reviews stay the separate per-lens agents; security is
  `aav-rust-security`; the final trim/separator/fmt pass is brain-meta-style + the aav-style-* suite.
- deploy/infra is its own standing default - see [[principle-25-deploy-infra]].

## why
re-deciding settled choices wastes my attention ([[intent-craft]]) and the choices are grounded in
what i trust ([[intent-trust]] - i picked criterion/winnow for real reasons). a standing default is a
form of leverage: i shouldnt have to say it twice.

## how to apply
- need a bench? criterion. a parser? winnow. python tooling? uv. dont ask which.
- if a standing default is genuinely wrong for the case, say so and ask - dont silently swap it.
- when you learn a new standing decision from me, the brain-meta-curate skill records it here.

## anti-pattern
proposing a custom bench harness when criterion is the standing choice; reaching for a different
parser than winnow without reason; pip/venv instead of uv.
