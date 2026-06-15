# schema: principle card

every belief in the brain is one atomic card (zettelkasten / basic-memory style: one idea per note,
densely linked). cards live in brain/principles/. interests live in brain/intents/ and use the
`kind: interest` variant.

## frontmatter
```yaml
---
name: principle-NN-short-slug      # unique, kebab-case, matches filename
kind: principle                    # principle | interest
rule: <one sentence, the imperative>      # principle only
interest: [intent-x, intent-y]     # which interest(s) this serves (principle only)
# note: interest cards do NOT author served_by - the graph derives it as the
# inverse of serves, so each principle declares its interests once (no drift).
confidence: very-high | high | medium     # how strong the evidence is
evidence_count: <int>              # rough count of corpus occurrences
tells: ["verbatim phrase", ...]    # exact phrases that signal this card; used by brain-recall matching
---
```

## body sections (in order)
1. `# PNN - title` : the card heading.
2. rule : the imperative, restated with nuance.
3. why : the interest it serves, linked [[intent-...]]. this is the positions->interests bridge: the
   rule is the position, the why is the interest.
4. how to apply : concrete, situational; when it dominates vs yields to another card.
5. verbatim tells : real quotes from the corpus (evidence; keeps the card honest).
6. anti-pattern : what draws a correction or heat; link [[principle-15-tone-is-signal]] if it triggers heat.

## linking rules
- link liberally with [[card-name]]. a link to a not-yet-written card is fine; it marks a gap to fill.
- every principle links to >=1 interest via `interest:`; the reverse served_by edge is derived by
  the graph, never authored on the interest card.
- when two cards tension (e.g. P01 ask-first vs P10 execute-through), each names the other and states
  which regime makes it dominant.

## lifecycle
- the brain-meta-curate skill creates/updates cards from new feedback (self-editing memory).
- evidence_count and tells are refreshed when `bin/brain-extract.py` re-runs.
- wrong/outdated cards are deleted, not left to rot.
