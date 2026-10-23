# brain store index (manifest)

the queryable store. tiered after memgpt/letta: a small always-loaded core, a larger retrieved
corpus, a deterministic graph over that corpus, and evidence derived from raw transcripts. query it
with [[../bin/run/brain-recall]] (graph traversal).

## tier 1: core (always loaded when the brain acts)
- [[CONSTITUTION]] : prime rule, who i am, the operating loop, the hard rules, voice.

## tier 2: principles (retrieved on demand; one belief per card)
- [[principles/principle-01-no-assumptions]] : ask under any ambiguity
- [[principles/principle-02-plan-before-build]] : small verbose plan + worked example
- [[principles/principle-03-review-gate]] : cold independent multi-lens gate, scheduled by diff size (brain-gate.py), 2-6 reviewers, two rounds
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
- [[principles/principle-30-deterministic-flow]] : follow flow.toml (sequence), separate from graph.json (context)
- [[principles/principle-31-libraryfy-shared]] : library-fy shared datatypes/helpers; never redefine a struct twice
- [[principles/principle-32-portability]] : discover the root, never hardcode a path or assume a fixed layout
- [[principles/principle-33-git-is-not-a-blocker]] : git is his; never perform it, never gate work on repo state
- [[principles/principle-34-untrusted-input]] : filenames, plans and caches are attacker-controlled; neutralise at the boundary
- [[principles/principle-35-gates-are-agent-side]] : "don't pause" means don't ask him; it never means skip the gate
- [[principles/principle-36-verify-with-stderr-visible]] : a verification that hides stderr or reads $? after a pipe is not one
- [[principles/principle-37-comment-the-artifact-not-the-edit]] : a comment describes the code as it now stands, never the edit that produced it
- [[principles/principle-38-a-non-answer-is-not-consent]] : a question he declined is unanswered, never assent - re-ask it, never resolve it with the brain's own lean
- [[principles/principle-39-style-contract]] : resolve each language's style before writing it; the STYLE gate proves the result rather than asserting it
- [[principles/principle-40-idiom-needs-exemplars]] : "be idiomatic" changes nothing; every idiom rule carries a before/after pair and the writer is shown the pairs
- [[principles/principle-41-rigor-scales-with-purpose]] : scratch skips idiom, tutorial adheres lightly, production is exhaustive - purpose is asked, never inferred
- [[principles/principle-42-plain-english-questions]] : current flow is X, proposed flow(s) and options are Y, in plain english - never syntax or jargon
- [[principles/principle-43-report-state-not-changelog]] : done or not done and what is left - never a tour of what was fixed; usage is a one-liner
- [[principles/principle-44-build-from-nothing-to-something]] : he learns by building a ladder atomically, each step from the last one's output, interactive and self-checking - never by memorizing a finished artifact
- [[principles/principle-45-scope-is-the-ask]] : a change does what was asked and stops; adjacent cleanup nobody asked for is what turns a two-step task into a review loop
- [[principles/principle-46-stay-in-the-working-folder]] : the folder he named is the whole world of a task; toolchain caches may be read, his other repos and files never - ask first
- [[principles/principle-47-copy-raw-fetches-into-the-repo]] : every fetched page lands in the repo's source corpus as it is fetched and the citing row names the copy; an uncopied fetch does not exist
- [[principles/principle-48-look-at-the-rendered-output]] : green checks are not a pass - rasterise/screenshot and read the pdf, chart, page or app before calling it done, with a scripted audit of what an eye misses
- [[principles/principle-49-his-interactive-app-shape]] : 3d stage first, click a point for its page on a stack, sliders for what matters, questionnaire-first persisted settings, receipt totals, 90's page + harsh retro scene, touch on his surface pro and phone, settings/filters relay live to every surface at once
- [[principles/principle-50-the-standing-mission]] : a worker carries the run's END GOAL, not just the phase's ask - work that moves the mission is kept even when it exceeded the sentence
- [[principles/principle-51-spaghetti-is-a-design-fault]] : when every available fix makes the code worse the DESIGN is the defect - or the review count stops dropping - leave the impl loop for DESIGN, redesign that one part, destructive proposals sanctioned
- [[principles/principle-52-parallel-dispatch]] : fan two or three independent workers out in ONE message on disjoint file sets or their own worktrees; the tree-wide build/test/lint command stays with the overseer and runs one at a time
- [[principles/principle-53-rigor-scales-with-the-change]] : the cold multi-lens review is bought by the size and kind of the CHANGE, never by a phase ending - a patchwork fix takes the mechanical check alone
- [[principles/principle-54-a-count-is-a-measurement]] : a count in a document is a measurement with a timestamp - re-measure, correct it, move on; never a finding, never a gate
- [[principles/principle-55-the-run-is-visible]] : a long run's state - flow stage, plan phase, what runs, what is left - is a page he can open, hosted locally and kept current
- [[principles/principle-56-close-out-housekeeping]] : at CLEANUP (before the commit) sweep what the work obsoleted unprompted - executed plans, resolved todos, closed items, one-off scripts, old caches, stale worktrees, old docs - keep exactly what he names, say in one line what went
- [[principles/principle-57-user-docs-are-an-icd]] : docs and replies read like a textbook (noun headings, imperative instructions, no openers or filler); user-facing docs teach usage in an ICD register - bullets/tables/snippets over prose, no code in sentences, mechanisms shown as a story, the smallest format per item
- [[principles/principle-58-a-correction-is-a-class]] : one flagged instance names a class - fix every instance everywhere in the same pass, and self-check before handing back
- [[principles/principle-59-cli-shows-the-commands-it-runs]] : a tool acting on machines shows what it resolved, lists the exact commands, asks once, then `Running: <cmd>` before each - every printed line re-runnable
- [[principles/principle-60-device-facing-code-is-gated-by-a-live-run]] : mocked-green is not done for code that acts on devices/hosts/buckets - run his real command against each target; tests stay local
- [[principles/principle-61-private-infra-stays-out-of-tracked-files]] : his real hosts, LAN ips and device ids live in live runs, plans/ and memory - tracked docs, tests and source carry placeholders; he squashes on merge so fix forward, never rewrite
- [[principles/principle-62-a-requested-separate-agent-is-dispatched-not-simulated]] : when he asks for a separate subagent, dispatch it and relay between agents; never fold the work into the asking agent, and none-found is a valid answer
- [[principles/principle-63-brainstorming-does-not-change-the-plan]] : an exploratory question gets an answer only; the live plan is untouched until he says change it
- [[principles/principle-64-resume-after-interruption-verifies-then-redispatches]] : after a restart verify each worker, recover its output or re-dispatch; never assume done
- [[principles/principle-65-numbered-recommendations-get-one-word-replies]] : numbered items with a recommended default so he can answer "affirm"; overrules are about extensibility or configurability
- [[principles/principle-66-open-items-are-one-file-each]] : one file per open item in plans/open-items/, fixed shape, sha256 footer detects his edits (brain-open-items.py)
- [[principles/principle-67-merge-keeps-both-prioritises-one]] : diverged machines: fold true duplicate rules, but keep both competing mechanisms with a priority and prune later; everything ends on main, staged not committed

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
  `bin/store/brain-graph.py`, gitignored, rebuilt on demand by brain-recall when a card is newer.

## tier 3: evidence (machine-derived; regenerate with `python3 bin/store/brain-extract.py`)
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
