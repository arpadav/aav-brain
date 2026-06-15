# plan: find_brain() single-repo rework + minimal brain env vars

## goal
collapse `find_brain()` from a two-repo `(aav_brain, agents_brain)` tuple to a single repo root (the
merge deleted the sibling `agents/` repo; agents + skills now live under `aav_brain/agentic-files/`),
and reduce the brain's env vars to the one irreducible anchor `AAV_BRAIN` (drop `AAV_BRAIN_BIN` and
`BRAIN_AGENTS`, both derivable). staged now; ACTIVATES at the cutover, not before.

## settled context
- the MERGE_AGENTS_INTO_BRAIN plan is sanctioned; phases 0-3 are done in this working tree, so
  `aav_brain/agentic-files/{agents,skills}` already exist and are populated.
- "don't commit" = no literal `git commit`; editing the live nix home repo + any file is fine.

## the one consumer that actually needs the agents path
`find_brain()` has 5 callers; four use only `aav_brain` (`brain-cards`, `brain-trace`, `brainlib:409`,
and `brain-find`). The ONLY consumer of `agents_brain` is `brain-flow.py:200`, the owner-existence gate:
it lists the skills dir to validate that every flow `owner` is a real skill. post-merge that dir is
`aav_brain/agentic-files/skills` - same 12 skill names, new location.

## worked example (validate the design on real discovery paths, post-merge)
1. **a brain script** - `brain-cards.py` calls `find_brain()`. `brainlib.py` lives at
   `aav-brain/bin/brainlib.py`, so self-location `__file__.parent.parent` = `~/repos/personal/aav-brain`,
   `<root>/brain/CONSTITUTION.md` exists -> returns that single root. cards = `<root>/brain`. (this
   branch already wins today; it just stops returning a phantom sibling.)
2. **a skill** - `brain-plan` runs `eval "$(brain-find --export)"`. post-rework `--export` prints exactly
   ONE line: `export AAV_BRAIN=/home/arpad/repos/personal/aav-brain`. the skill then reads
   `$AAV_BRAIN/brain/CONSTITUTION.md` and lists `$AAV_BRAIN/agentic-files/skills`. no `$BRAIN_AGENTS`,
   no `$AAV_BRAIN_BIN`.
3. **the owner gate** - `brain-flow.py` does `skills_dir = find_brain() / "agentic-files" / "skills"`,
   reads the 12 dir names, validates every flow owner against them + the `{worker, -,
   brain-review-gate, brain-verifier}` whitelist. passes (same names, new path).
4. **the symlink fallback** (no `__file__`, e.g. a foreign caller) - `~/.agents/skills/brain-plan`
   resolves through the home-manager->nix->repo chain to `<root>/agentic-files/skills/brain-plan`;
   `link.resolve().parents[2]` = `<root>` (brain-plan -> skills -> agentic-files -> root), confirmed by
   `<root>/brain/CONSTITUTION.md`. (old math was `.parent.parent`, one level shallower, for the old
   `agents/brain/skills/` nesting.)

## phases (atomic; staged in the working tree; ACTIVATE together at cutover)

### phase 1 - `find_brain()` returns a single root  (`bin/brainlib.py`)
- return a bare `Path` (the repo root), not a tuple. update all three branches:
  - self-loc: `return here` (drop `here.parent / "agents" / "brain"`).
  - skill-symlink: `aav_brain = link.resolve().parents[2]`; confirm `<aav_brain>/brain/CONSTITUTION.md`;
    `return aav_brain`.
  - fallback: `return guess`.
- rewrite the docstring (one repo; agents/skills derive under `agentic-files/`).
- acceptance: `python3 -c "from brainlib import find_brain; print(find_brain())"` prints the root.

### phase 2 - update the 4 simple callers
- `brain-cards.py:90`, `brain-trace.py:70`, `brainlib.py:409`: `aav_brain, _ = find_brain()` ->
  `aav_brain = find_brain()`.
- `brain-flow.py:200`: `_, agents_brain = find_brain(); skills_dir = agents_brain / "skills"` ->
  `skills_dir = find_brain() / "agentic-files" / "skills"`.
- acceptance: `brain-cards.py`, `brain-graph.py --check`, `brain-flow.py --check`, `brain-trace.py
  --against` all run green.

### phase 3 - `brain-find.py`: emit only `AAV_BRAIN`  (`bin/brain-find.py`)
- `main()`: `aav_brain = find_brain()`. selectors: `--aav` -> root; `--agents` ->
  `root/agentic-files/agents`; `--skills` (new) -> `root/agentic-files/skills`; `--bin` -> `root/bin`;
  `--export` -> ONLY `export AAV_BRAIN=<root>`; default -> `<root>`.
- rewrite the comment block: one repo, one anchor; agents/skills/bin all derive from `$AAV_BRAIN` (or
  `brain-find --agents/--skills/--bin`), none is its own var (P32).
- acceptance: `brain-find --export` prints exactly one line; `brain-find --agents` ->
  `.../agentic-files/agents`.

### phase 4 - reduce home.nix env vars  (`home/home.nix`)  [activates on `re`]
- `sessionVariables`: KEEP `AAV_BRAIN`; DELETE `AAV_BRAIN_BIN` (line 183) and `BRAIN_AGENTS` (line 184).
- update the `let`-block bootstrap comment (13-16) to drop the `AAV_BRAIN_BIN`/two-anchor language.
- acceptance: after `re`, `env | grep -c BRAIN_AGENTS` = 0; `$AAV_BRAIN` still resolves.

### phase 5 - rewrite skill `$BRAIN_AGENTS` references  (`agentic-files/skills/*/SKILL.md`)
- the 4 bootstrap comments "`# sets $AAV_BRAIN and $BRAIN_AGENTS`" (brain-meta-drive, brain-review,
  brain-execute, brain-meta-recall) -> "`# sets $AAV_BRAIN`".
- `brain-self-refine` lines 34/35/44: `$BRAIN_AGENTS/skills` -> `$AAV_BRAIN/agentic-files/skills`; the
  hardcoded-path grep targets become `"$AAV_BRAIN/bin" "$AAV_BRAIN/agentic-files"`.
- acceptance: `grep -rn 'BRAIN_AGENTS\|AAV_BRAIN_BIN' agentic-files bin` returns nothing.

## timing / safety (why "activate at cutover", not piecemeal)
phases 1-2 are inert-safe today (scripts self-locate; the new `agentic-files/skills` already exists).
but phase 3 drops `BRAIN_AGENTS` from `--export`, and the LIVE pre-cutover skills (loaded from the
sibling `agents/brain/skills`) still read `$BRAIN_AGENTS` via the SAME `brain-find.py` - so applying
phase 3 before the live skills become the `agentic-files` ones would break them. therefore: stage all 5
phases now, ACTIVATE them as one bundle at the cutover (the `re` switch + agents-repo archival in
HOME_NIX_CUTOVER.md). this supersedes that doc's deferred "update find_brain" note - fold this plan in
as the concrete diff.

## review-gate strategy
one cold `brain-review-gate` pass on the staged diff (correctness lens for the discovery logic +
parents[2] nesting math; a path lens for the derive helpers), then the brain-guided would-arpad pass.
`brain-verifier` runs the real checks: `brain-cards/graph/flow`, a clean-shell discovery smoke test, and
the zero-residual greps. correctness -> fix -> fmt last.

## reuse + minimal surface (P05/P14)
reuse `find_brain()`'s existing 3-branch resolution - only collapse the return and fix the symlink
nesting; no new discovery mechanism. the minimal var set is ONE: `AAV_BRAIN`. everything else derives.

## open decisions (settle these; my lean noted)
- **D1 env-var floor**: keep `AAV_BRAIN` as one persistent sessionVariable (min = 1, ergonomic for
  ad-hoc shells) vs drop all three and have `AAV_BRAIN` exist ONLY as the runtime `brain-find --export`
  (min = 0 persistent, purest P32). lean: **keep `AAV_BRAIN`** - it is the irreducible anchor and you
  type `$AAV_BRAIN/...` interactively. would arpad keep the one anchor, or go fully discovery-only?
- **D2 brain-find selectors**: keep `--agents`/`--skills`/`--bin` as derive-on-demand helpers vs drop
  `--agents` (no longer a separate repo). lean: keep all three - harmless, and skills/tooling may want
  the skills/agents dir without hardcoding `agentic-files/`.
- **D3 return type**: `find_brain()` returns a bare `Path` vs a 1-field namedtuple for caller symmetry.
  lean: bare `Path` - `root = find_brain()` reads cleanest; the four `, _` unpacks go away.
- **D4 backward-compat**: clean single-layout `find_brain` activated at cutover vs a dual-layout probe
  (try `agentic-files/`, fall back to the sibling) so it can land live before cutover. lean: clean +
  at-cutover - the cutover is atomic and imminent; dual-layout is transient complexity for a window
  that closes immediately. would arpad want it inert-until-cutover, or live-early with a fallback?

## what's yours
the `re` switch (phase 4 activation) and the cutover sequencing in HOME_NIX_CUTOVER.md. the brain stages
the edits and never commits.
