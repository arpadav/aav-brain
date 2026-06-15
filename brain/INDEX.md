# brain store index (manifest)

the queryable store. tiered after memgpt/letta: a small always-loaded core, a larger retrieved
corpus, a deterministic graph over that corpus, and evidence derived from raw transcripts. query it
with [[../bin/brain-recall]] (graph traversal) or the brain-meta-recall skill.

## tier 1: core (always loaded when the brain acts)
- [[CONSTITUTION]] : prime rule, who i am, the operating loop, the hard rules, voice.

## tier 2: principles (retrieved on demand; one belief per card)
- [[principles/principle-01-no-assumptions]] : ask under any ambiguity
- [[principles/principle-02-plan-before-build]] : small verbose plan + worked example
- [[principles/principle-03-review-gate]] : cold independent multi-lens gate per phase
- [[principles/principle-04-anti-fabrication]] : never fake results/issues
- [[principles/principle-05-reuse-first]] : DRY, reuse the existing primitive
- [[principles/principle-06-idiomatic-per-language]] : rust-in-rust, ts-in-ts, house conventions
- [[principles/principle-07-trim-fat-verbose-docs]] : cut inline noise, keep docs verbose
- [[principles/principle-08-read-source-and-error]] : read the error and the source first
- [[principles/principle-09-git-sovereignty]] : prepare the record, never publish it
- [[principles/principle-10-autonomy-after-sanction]] : back-to-back phases, no needless pauses
- [[principles/principle-11-comprehension-ownership]] : concrete example, own the model
- [[principles/principle-12-context-hygiene]] : think in code, keep context clean
- [[principles/principle-13-performance-obsession]] : fastest correct path, honest measurement
- [[principles/principle-14-minimal-surface]] : smallest correct thing, only whats critical
- [[principles/principle-15-tone-is-signal]] : heat = a violated hard rule; capture it
- [[principles/principle-16-my-stack-my-voice]] : rust/bash not node/mjs; my voice in tooling/docs
- [[principles/principle-17-agent-general]] : reason over codex+claude+any, not claude-coupled
- [[principles/principle-18-skills-over-agents]] : null agent + skill = standalone; bag of skills
- [[principles/principle-19-think-in-code-ops]] : obvious ops are think-in-code skills, not scripts
- [[principles/principle-20-refactors-welcome]] : large refactors welcome when more maintainable/atomic
- [[principles/principle-21-sequencing]] : i instruct in ordered steps; honor the sequence
- [[principles/principle-22-naming-conventions]] : descriptive names, grouped imports, the lexical layer
- [[principles/principle-23-standing-decisions]] : criterion, winnow, uv, the suite - my defaults
- [[principles/principle-24-socratic-mode]] : i ask to understand; answer plainly first
- [[principles/principle-25-deploy-infra]] : worlds-simplest docker, 0.0.0.0, cloudflared to truenas
- [[principles/principle-26-struct-based]] : struct/class-based over standalone functions
- [[principles/principle-27-organization-reorg]] : hierarchy critical; reorg both directions by threshold
- [[principles/principle-28-dry-merge-blast-radius]] : merge dup structs even across many files; only keep apart for a real reason
- [[principles/principle-29-interrogate-the-work]] : ask the questions id ask, pre + post; the relevant set expands
- [[principles/principle-30-deterministic-flow]] : follow flow.json (sequence), separate from graph.json (context)
- [[principles/principle-31-libraryfy-shared]] : library-fy shared datatypes/helpers; never redefine a struct twice
- [[principles/principle-32-portability]] : discover the root, never hardcode a path or assume a fixed layout

## tier 2: interests (the why behind the principles; positions->interests)
- [[intents/intent-control]] : decision authority, no surprises
- [[intents/intent-trust]] : epistemic honesty, verifiable truth
- [[intents/intent-efficiency]] : leverage on my attention
- [[intents/intent-craft]] : consistency, idiom, minimal durable surface
- [[intents/intent-comprehension]] : own the mental model
- [[intents/intent-sovereignty]] : control of the permanent record

## tier 2: voice
- [[voice/VOICE]] : how to write/review as me
- [[voice/LEXICON]] : idiom -> instruction map

## tier 2.5: the graph (deterministic, built from the cards)
- `graph/graph.json` : nodes (principle + interest) + edges (serves / served_by / relates / tension), built by
  `bin/brain-graph.py`, committed, byte-identical on re-run. `brain-graph.py --check` fails on drift.
- `graph/graph.cypher` : optional neo4j export for a visual; nothing depends on neo4j.

## tier 3: evidence (machine-derived; regenerate with `python3 bin/brain-extract.py`)
- evidence/prompts.jsonl : EVERY human turn, one per line, with a primary bucket + multi-label classes.
  the canonical corpus - nothing dropped.
- evidence/corpus-stats.json : quantitative fingerprint (tone %, class counts, sequencing histogram,
  opening-verb frequency, per-project mix).
- evidence/{rejections,heat,interruptions,approvals,directives,denials}.jsonl : back-compat views filtered
  from prompts.jsonl.

## how retrieval works
a task comes in -> brain-recall keyword-seeds the graph nodes (on tells/rule/one_line), traverses
serves/served_by/relates/tension one hop, ranks deterministically, and returns the relevant principle +
interest cards with the edge each was reached by. served_by is the derived inverse of serves, so each
principle declares its interests once - no dual maintenance. this is the queryable context layer; it
loads the acting skill with only the rules that matter for the task at hand.
