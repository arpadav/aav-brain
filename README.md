# aav-brain

my second brain for dev work. it learns how i plan, review, write, and push back from my real agent
transcripts (codex + claude), then acts as me: reviews other agents work, writes prompts in my voice,
supervises a plan by dispatching other agents. it doesnt fabricate and it doesnt publish.

this is ONE repo: the doctrine (`brain/`), the tooling (`bin/`), and the acting suite
(`agentic-files/` - skills + agents) that home-manager links into claude + codex. private memory
(evidence + trace) lives in the `logs/` submodule, never in this repo's history.

> human-facing doc - nothing reads this at runtime. the authoritative sources are
> `brain/CONSTITUTION.md`, the cards, and `brain/flow/flow.toml`.

## why
i delegate to AI for leverage, not to hand off judgment. the brain is the part that stays in the loop
when i step away: call /brain-execute and it picks up a plan, dispatches workers, gates each phase
cold, refuses to fabricate, stops only on real ambiguity, prepares the commit. it doesnt publish it.

## layout
```
aav-brain/             the one transferable brain (a `brain` submodule of home)
  README.md            you are here
  ARCHITECTURE.md      the system: memory tiers, the 4 entries + brain-meta-* machinery + agents
  brain/               the queryable DOCTRINE store (committed, public knowledge)
    CONSTITUTION.md    tier-1 core: the hard rules + voice (always loaded)
    principles/        atomic principle cards (one belief each)
    intents/           interest cards (the why)
    voice/             how to write/review as me
    flow/  graph/      the deterministic flow + the graph derived from the cards
    INDEX.md           the store manifest
  agentic-files/       the acting suite (home-manager links it into claude + codex)
    skills/            the 12 skills (universal SKILL.md across claude / codex / ~/.agents)
    agents/            categorized: brain/  general/  lang/rust/  custom/
  bin/                 all tooling: brain-find, -recall, -cards, -graph, -flow, -trace, -walk,
                       -fmt, -extract, compile (brainlib is the shared lib)
  .generated/          codex TOML agents, compiled on every switch (GITIGNORED)
  logs/                PRIVATE memory submodule (aav-brain-logs): evidence + trace. its content
                       lives in a separate private repo, never here; the scripts write to it via
                       the XDG symlink ~/.local/share/aav-brain -> logs/ (brainlib.find_data).
  docs/                FINGERPRINT, INTENT_MAP, DEV_FLOWCHART, PRIOR_ART
  schema/              the card / flow / trace schemas
  plans/               worked plans (brain-plan writes here)
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

the acting suite lives in `agentic-files/` (home-manager links it into ~/.claude and ~/.codex). use the
FOUR entrypoints (the only skills you call):
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
