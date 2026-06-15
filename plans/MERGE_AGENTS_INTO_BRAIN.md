# plan: merge `agents` repo into `aav-brain` (the one transferable AI brain)

## goal
collapse `~/repos/personal/agents` into `aav-brain` so ONE repo holds the whole AI workflow: the
brain (cognitive core), its scripts, the agents, and the skills. decouple project/machine-specific
agents into general-purpose ones, categorize the agentic files, template agents to both claude (`.md`,
the tracked source) and codex (`.toml`, generated + gitignored), then wire it into `home` as a single
submodule. fresh history. NOTHING is committed by the brain - arpad commits.

## settled (this session)
- structure: brain = the TOOL (cards + scripts); the agentic files (agents + skills) are SEPARATE,
  grouped under their own umbrella - not interleaved with `brain/` and `bin/`.
- codex consumes TOML agents (web-confirmed: `~/.codex/agents/*.toml`, one per agent, required keys
  `name` / `description` / `developer_instructions`; the rest inherit). skills stay universal `SKILL.md`.
- templating model: the agent `.md` is the TRACKED source of truth (claude reads it raw); templating
  generates ONLY the codex `.toml`, which is gitignored.
- seeding: a NEW `git@github.com:arpadav/aav-brain`, fresh history (plain moves), old `agents` repo
  archived/deleted after cutover.

## target structure
```
aav-brain/                       # the one repo; becomes a `home` submodule
├── brain/                       # THE TOOL, pt.1 - cognitive core (cards). UNCHANGED.
│   └── CONSTITUTION.md INDEX.md principles/ intents/ flow/ graph/ trace/ voice/ evidence/
├── bin/                         # THE TOOL, pt.2 - all scripts: brain-* + brainlib + compile.py (moved in)
├── agentic-files/               # SEPARATE from the tool - the deployable artifacts
│   ├── agents/                  #   tracked .md sources, categorized:
│   │   ├── brain/               #     brain-internal: brain-review-gate, brain-verifier
│   │   ├── general/             #     cross-language: semantic-architecture-reviewer (DECOUPLED)
│   │   ├── lang/rust/           #     idiomatic-{api,flow,types,organization}, rust-{perf,security,implementer},
│   │   │                        #       style-{docs,imports,items,separators}
│   │   └── custom/              #     experiments: slot-game-architect
│   └── skills/                  #   the 12 skills (universal SKILL.md), tracked, raw
├── .generated/                  # GITIGNORED templating output
│   └── codex/agents/<name>.toml #   one codex agent per source .md
├── docs/ schema/ plans/ README.md ARCHITECTURE.md
└── .gitignore                   # + .generated/
```
`agentic-files/` is a working name (open decision D1). brain skills stay flat under
`agentic-files/skills/` (only 12); agents get the category tree because they span brain/general/lang/custom.

## worked example (validate the design on ONE agent + ONE skill before trusting it)

**agent `aav-rust-implementer` (claude-native md → codex toml):**
1. source of truth, tracked, claude reads it raw:
   `agentic-files/agents/lang/rust/aav-rust-implementer.md` (unchanged content; just relocated).
2. `python3 bin/compile.py` reads that `.md`, strips the claude-only `model:`/`color:` frontmatter and
   the `<example>` blocks from the description, and writes the gitignored:
   `.generated/codex/agents/aav-rust-implementer.toml` ->
   ```toml
   name = "aav-rust-implementer"
   description = "The single Rust IMPLEMENTER for Arpad's work — writes Rust that already satisfies the idiomatic + perf doctrine. Dispatched in place of the generic rust-engineer."
   developer_instructions = '''
   You are a senior Rust systems and performance engineer ...
   <the entire agent body, verbatim>
   '''
   ```
   (body uses a TOML literal `'''...'''` so backslashes/quotes need no escaping; compile.py guards the
   rare case of `'''` appearing in a body.)
3. home.nix symlinks: `.claude/agents/lang/rust` -> `aav-brain/agentic-files/agents/lang/rust` (claude
   gets the `.md`); `.codex/agents` <- `aav-brain/.generated/codex/agents` (codex gets the `.toml`).
4. result: claude dispatches `aav-rust-implementer` from the `.md`; codex spawns the same agent from the
   `.toml`; one source, two surfaces, the `.toml` never tracked.

**skill `brain-plan` (universal, no templating):**
1. `agentic-files/skills/brain-plan/SKILL.md` - tracked, raw.
2. NO generation. home.nix symlinks it as-is into `.claude/skills/brain-plan`,
   `.codex/skills/brain-plan`, `.agents/skills/brain-plan` (mkOutOfStoreSymlink, live).
3. result: identical SKILL.md across all three surfaces, exactly as today.

## phases (atomic, ordered, each cold-gated; nothing committed)

### phase 0 - skeleton + prereqs (no file moves yet)
- create the empty target tree in aav-brain: `agentic-files/agents/{brain,general,lang/rust,custom}`,
  `agentic-files/skills/`, `.generated/`. add `.generated/` to `.gitignore`.
- [arpad runs] create the empty `git@github.com:arpadav/aav-brain` remote (needed in phase 4 for the
  submodule; not wired yet). don't push.
- acceptance: tree exists; `.gitignore` covers `.generated/`; `brain-cards.py`/`graph`/`flow --check`
  still green (nothing touched yet). gate: structural only.

### phase 1 - relocate the agentic files (copies; fresh history; agents repo still live)
- copy the 13 `aav-*.md` + 2 brain agents into the category tree:
  - `lang/rust/`: idiomatic-rust-{api,flow,types,organization}, rust-{perf,security,implementer},
    style-{docs,imports,items,separators}
  - `general/`: semantic-architecture-reviewer
  - `custom/`: slot-game-architect
  - `brain/`: brain-review-gate, brain-verifier
- copy the 12 skills into `agentic-files/skills/`.
- move `agents/brain/bin/compile.py` -> `aav-brain/bin/compile.py`; fix its `sys.path` bridge (it now
  imports `brainlib` from its OWN `bin/`, not `../../../aav-brain/bin`).
- drop the per-skill `scripts/ -> ../../../../aav-brain/bin` symlinks (D6): bootstrap is `brain-find` on
  PATH, already installed by home.nix.
- DO NOT touch the live `agents` repo or home.nix yet - both keep working.
- acceptance: tree matches target; `compile.py` imports cleanly; cards/graph/flow still green.
  gate: cold review of the moved tree + would-arpad pass on the layout (P29).

### phase 2 - decouple (P32 + project-coupling, the "transferable" requirement)
- rewrite `general/semantic-architecture-reviewer.md`: drop "Inspectra"; drop the hardcoded
  `ixa-core/types/api/io/inference` layering and the "Inspectra-specific rules (from CLAUDE.md)" hook;
  replace with: DISCOVER the current repo's crate/module layout and read the current repo's
  `CLAUDE.md`/`AGENTS.md` generically. keep the method (semantic placement, DRY, push primitives to the
  lowest layer). the examples become layout-agnostic.
- normalize every hardcoded `/home/arpad/.claude/agent-memory/...` -> `~/.claude/agent-memory/...`
  across the coupled files (idiomatic ×4, perf, security, style ×4, semantic-reviewer, slot). the new
  `rust-implementer` is already clean - it is the template.
- acceptance: `grep -rnE 'inspectra|ixa[-_]|/home/[a-z]' agentic-files/` returns nothing real; each
  decoupled agent reads against the current repo, not a named one. gate: cold review FOCUSED on residual
  coupling + a would-arpad pass ("would arpad ship this as transferable?").

### phase 3 - dual-format templating (md source -> codex toml, gitignored)
- extend `bin/compile.py`: for each `agentic-files/agents/**/*.md`, emit
  `.generated/codex/agents/<name>.toml` with `name`, `description` (reuse the existing
  `codex_description()` example-stripper), `developer_instructions = '''<body>'''`. keep the
  `brainlib.Artifact` drift-gate; since the target is gitignored, `--check` becomes an IDEMPOTENCY gate
  (regenerate, byte-compare in memory) run on init/CI, not a committed-artifact diff (D4).
- skills are NOT templated (universal SKILL.md already serves all three surfaces).
- acceptance: `python3 bin/compile.py` writes valid TOML (parse each with `tomllib`); `--check` is
  idempotent; `.generated/` is gitignored and un-tracked. gate: cold review + `brain-verifier` actually
  runs compile + parses the toml (anti-fabrication, P04).

### phase 4 - home.nix cutover (point everything at aav-brain; add the submodule; template on switch)
- [arpad runs] add aav-brain as a `home` submodule; remove the `agents` submodule
  (`.gitmodules` + `git rm`). order: ADD aav-brain + repoint nix FIRST, REMOVE agents submodule second.
- rewrite home.nix:
  - collapse `brain` + `aavBrain` to one path (the aav-brain submodule).
  - skills: `mkLinks .claude/skills | .agents/skills | .codex/skills <- aav-brain/agentic-files/skills`.
  - claude agents: symlink the category dirs into `.claude/agents/` (today claude reads ONE level of
    subdir: `.claude/agents/aav`, `.claude/agents/brain`). the repo keeps the `lang/rust/` hierarchy,
    but the SYMLINK layer flattens to one level - e.g. `.claude/agents/rust -> .../agents/lang/rust`,
    `.claude/agents/general -> .../agents/general`, etc. (verify claude's recursion depth first - D8).
  - codex agents: `.codex/agents <- aav-brain/.generated/codex/agents` (was `.codex/skills` - codex now
    has a real agents dir).
  - `home.activation` step: run `python3 .../bin/compile.py` on `re` so `.generated/` is built before
    the symlinks resolve.
  - env: keep `AAV_BRAIN`; retire `BRAIN_AGENTS` (or repoint to aav-brain); `AAV_BRAIN_BIN` unchanged.
- acceptance: `re` (home-manager switch) succeeds; `.claude/skills`, `.claude/agents/*`, `.codex/agents`
  all resolve into aav-brain; the codex `.toml`s exist; a dispatch smoke-test of one agent + one skill on
  BOTH claude and codex. gate: `brain-verifier` runs the switch + smoke test; cold review of the nix diff.

### phase 5 - retire the agents repo
- [arpad runs] delete/archive `~/repos/personal/agents` once phase 4 is verified.
- sweep: `grep -rn 'repos/personal/agents' ~/.config/home-manager ~/.claude` returns nothing; all paths
  resolve through aav-brain. full reload smoke test.
- acceptance: nothing references the old repo; everything works from the single submodule. gate: final
  cold review + would-arpad pass on the whole merged repo.

## review-gate strategy (baked in)
each phase: cold/unguided `brain-review-gate` on that phase's diff ("surface every issue,
biggest-bug-to-smallest-nit"), THEN the independent brain-guided would-arpad pass (P29 superposition) -
"would arpad lay the tree out like this? write this decoupled agent like this?". phases 3 + 4 also get
`brain-verifier` (real compile / real `re` / real dispatch - no asserted success). correctness -> fix ->
style/fmt last. a single-lens nit blocks.

## reuse + minimal surface (P05/P14/P31)
- reuse `brainlib.Artifact`'s drift-gate for the codex compile - do NOT hand-roll a second build/check.
- reuse the existing `codex_description()` example-stripper.
- `aav-rust-implementer` is the portability template; the decouple pass conforms the others TO it.
- no new deps. compile.py stays stdlib (`tomllib` is read-only/3.11+; for WRITING toml, emit by hand -
  the schema is 3 scalar keys + one triple-quoted string, no lib needed).

## open decisions (would-arpad questions - options + my lean, you settle)
- **D1 umbrella name**: `agentic-files/` (your word) vs `surface/` vs flat `agents/`+`skills/` siblings.
  lean: `agentic-files/`, since you framed brain-as-tool / agentic-files-as-separate. would you name this
  folder this way?
- **D2 category names**: `lang/rust/` vs `languages/rust/` vs flat `rust/`; `general/` vs
  `general-purpose/`; `custom/` vs `experiments/`. lean: `lang/rust/`, `general/`, `custom/` (terse, P22).
- **D3 brain agents placement**: `agentic-files/agents/brain/` (with the others) vs a top-level spot next
  to skills. lean: under `agents/brain/` - they ARE agents, keep one agents root.
- **D4 drift gate**: keep `compile.py --check` as an idempotency gate (regen + compare in memory) vs drop
  it entirely now that output is gitignored. lean: keep it - cheap, and it catches a broken template.
- **D5 agent-memory**: leave learned notes machine-local at `~/.claude/agent-memory/...` (just made
  portable) vs move them INTO the transferable brain. lean: leave machine-local - they are per-machine
  project observations, not brain doctrine. would you want memory to travel with the brain?
- **D6 skill bootstrap**: drop the per-skill `scripts/` symlinks for `brain-find` on PATH (one bootstrap)
  vs keep both. lean: drop the symlinks (P32 - no layout-baking symlink).
- **D7 codex model mapping**: drop claude `model:`/`color:` (codex inherits) vs map `model:` -> codex
  `model`. lean: drop - let codex inherit the session model unless you want pinning.
- **D8 claude agent nesting** (surfaced by PLANPROBE): claude reads ONE subdir level under
  `.claude/agents/`. so the repo can keep `lang/rust/` but the symlinks must flatten to one level
  (`.claude/agents/rust`). lean: keep the deep repo tree, flatten at the symlink layer. confirm claude's
  recursion depth before phase 4 (if it recurses deeper, mirror the tree directly).

## what's yours to run (the brain never commits - P09)
creating the `aav-brain` GitHub remote; the submodule add/remove; deleting the `agents` repo; and every
`git commit`. the brain stages the working tree and stops.
