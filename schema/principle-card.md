# schema: principle card

every belief in the brain is one atomic card (zettelkasten / basic-memory style: one idea per note,
densely linked). cards live in brain/principles/. brain/intents/ holds the interest documents: they are prose a
human reads and valid [[link]] targets, and carry no tier.

## frontmatter
```yaml
---
name: principle-NN-short-slug      # unique, kebab-case, matches filename
kind: principle                    # principle | interest
tier: constitution|conditional|narrow  # REQUIRED on a principle. how the card REACHES an agent
                                   # (brainlib.vocab.Tier); measured, not asserted: see tiers.toml.
                                   # re-derive from that, never hand-promote a favourite.
rule: <one sentence, the imperative>      # principle only
interest: [intent-x, intent-y]     # which interest(s) this serves (principle only)
# a FIELD, not an edge: why intents are not graph nodes, see bin/brainlib/graph.py
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
- every principle names >=1 interest via `interest:`. it is metadata, not an edge; brain-cards.py
  fails on a name with no document in `brain/intents/`.
- when two cards tension (e.g. P01 ask-first vs P10 execute-through), each names the other and states
  which regime makes it dominant.

## lifecycle
- the brain-meta-curate skill creates/updates cards from new feedback (self-editing memory).
- evidence_count and tells are refreshed when `bin/store/brain-extract.py` re-runs.
- wrong/outdated cards are deleted, not left to rot.
