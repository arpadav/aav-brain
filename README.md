# aav-brain

my second brain for dev work. it learns how i plan, review, write, and push back from my real agent
transcripts (codex + claude), then acts as me: reviews other agents work, writes prompts in my voice,
supervises a plan by dispatching other agents. it doesnt fabricate and it doesnt publish.

this repo is the knowledge + docs + tooling. the skills + 2 agents that act live in a sibling repo:
../agents/brain/.

> human-facing doc - nothing reads this at runtime. the authoritative sources are
> `brain/CONSTITUTION.md`, the cards, and `brain/flow/flow.toml`.

## why
i delegate to AI for leverage, not to hand off judgment. the brain is the part that stays in the loop
when i step away: call /brain-execute and it picks up a plan, dispatches workers, gates each phase
cold, refuses to fabricate, stops only on real ambiguity, prepares the commit. it doesnt publish it.

## layout
```
aav-brain/
  README.md            you are here
  ARCHITECTURE.md      the system: memory tiers, the 4 entries + brain-meta-* machinery + 2 agents
  docs/
    FINGERPRINT.md     evidence-based report on my dev & writing ethos
    INTENT_MAP.md      positions -> interests (principled negotiation)
    DEV_FLOWCHART.md   the end-to-end state machine + node->owner map
    PRIOR_ART.md       what i borrowed (memgpt/letta, graphiti/zep, reflexion, getting to yes)
  brain/               the queryable store
    CONSTITUTION.md    tier-1 core: the hard rules + voice (always loaded)
    principles/        atomic principle cards (one belief each)
    intents/           interest cards (the why)
    voice/             how to write/review as me
    evidence/          machine-derived signal (regenerate any time)
    INDEX.md           the store manifest
  bin/
    brain-extract.py   mine ~/.codex + ~/.claude -> evidence (python/uv; re-run to refresh)
    brain-recall.py     retrieve the cards relevant to a task (bash/grep)
  schema/
    principle-card.md  the card schema
    optional-graph.md  neo4j/graphiti upgrade path (optional, infra-free by default)
```

## quickstart
```bash
# 1. (re)build the evidence from my real history. explicit signal only, no accepted-edit guessing.
python3 bin/brain-extract.py          # or: uv run bin/brain-extract.py

# 2. ask the brain what it knows about a task
python3 bin/brain-recall.py "rust idiomatic review, dont commit, dont fake the benchmark"

# 3. read the index
python3 bin/brain-recall.py --all
```

then install the acting suite from ../agents/brain/ and use the FOUR entrypoints (the only skills you call):
- /brain-plan <idea>: plan this new thing (or a change) my way, to sanction.
- /brain-execute: build a sanctioned plan to DONE - "continue" / "resume" picks it back up.
- /brain-review: cold multi-lens review of the current diff.
- /brain-self-refine: turn the review lens on the brain itself.

everything else is `brain-meta-*` machinery the entries load (the engine + node-owner skills) - dont
call it directly.

## the brains own rules (abridged)
1. consent is explicit, never inferred. an accepted edit is not approval; only spoken signal counts.
2. serve interests, not positions. decompose every demand into the need it serves and meet that.
3. know which regime youre in. ask before sanction; execute through after.
4. never fabricate. honest "its slower" beats a flattering fiction.
5. the git record is sovereign. prepare it; i commit it.
6. tooling in my stack & voice. rust/bash, never node/mjs. general agent brain, not claude-coupled.
7. learn continuously. every interruption and "no" updates a card.

see ARCHITECTURE.md for the design and docs/FINGERPRINT.md for the evidence. built by mining every
human turn across 45 claude projects + the full codex history. re-run brain-extract.py to keep it
current.
