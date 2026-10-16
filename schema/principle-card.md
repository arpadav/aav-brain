# schema: principle card

every belief in the brain is one atomic card (zettelkasten / basic-memory style: one idea per note,
densely linked). cards live in brain/principles/. brain/intents/ holds the interest documents: they are prose a
human reads and valid [[link]] targets, but they are NOT graph nodes, are never retrieved, and carry
no tier.

## frontmatter
```yaml
---
name: principle-NN-short-slug      # unique, kebab-case, matches filename
kind: principle                    # principle | interest
tier: constitution|conditional|narrow  # REQUIRED on a principle. how the card REACHES an agent, and
                                   # MEASURED rather than asserted. `constitution` loads on every
                                   # recall without being scored - it is for cards judged broadly
                                   # relevant that the scorer does not surface (one is judged
                                   # relevant on 28% of a labelled prompt set and served on 1% of
                                   # real recalls). `narrow` is the other end, rare and specific, and
                                   # clears a LOWER share-of-task floor because a floor tuned for
                                   # breadth would never admit one. `conditional` is the default and
                                   # covers most cards. see tiers.toml for the rule, the thresholds
                                   # and the measurement behind every assignment - re-derive from
                                   # that, never hand-promote a favourite.
rule: <one sentence, the imperative>      # principle only
interest: [intent-x, intent-y]     # which interest(s) this serves (principle only)
# note: this is a FIELD, not an edge. brain/intents/*.md stay on disk as prose
# and as valid [[link]] targets, but they are NOT graph nodes and are not
# retrievable. an intent is the WHY of its principles and never fires alone, so
# as peers they only ever co-occurred: measured on a labelled set,
# intent-comprehension and P11 were relevant on 86% of the same prompts while
# sharing 12% of their vocabulary - two nodes, one rule. four of the six also
# ranked in the graph's top five by fan-in, which is what made one of them the
# top card on 71% of the real prompt corpus.
confidence: very-high | high | medium     # how strong the evidence is
evidence_count: <int>              # rough count of corpus occurrences
binds: [code, python]              # OPTIONAL. contexts where this card loads REGARDLESS of score.
                                   # scoring is word-overlap between the task and the card, so a rule
                                   # phrased as a correction ("merge DRY-violating structs") scores 0
                                   # against a task phrased as a request ("write python scripts") and
                                   # never reaches the writer. a bind is that floor: `code` for any
                                   # code-writing task, plus a language tag for per-language extras.
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
- every principle names >=1 interest via `interest:`. it is metadata, not an edge - no serves or
  served_by edge is emitted, and nothing validates the name, so spell it carefully.
- when two cards tension (e.g. P01 ask-first vs P10 execute-through), each names the other and states
  which regime makes it dominant.

## lifecycle
- the brain-meta-curate skill creates/updates cards from new feedback (self-editing memory).
- evidence_count and tells are refreshed when `bin/store/brain-extract.py` re-runs.
- wrong/outdated cards are deleted, not left to rot.
