# Skill Suite Restructure — 4 entries over one multi-entry flow, machinery → brain-meta-*

> Sanctioned in SHAPE via the brain-self-refine trace (2026-06-14). This plan sequences the build.
> Lives in `$AAV_BRAIN/plans/`. Execution is brain-execute's job once blessed.

---

## Goal

Collapse the 11-skill suite into **4 user-callable entry skills** (`plan`, `review`, `execute`,
`self-refine`), each entering one **unified multi-entry `flow.json`** at its own node and traversing to
an END state via **one shared trampoline engine, `brain-meta-drive`**. All machinery renames to
`brain-meta-*`. `brain-continue` dissolves (its trampoline → `brain-meta-drive`; its build role →
`brain-execute`; "continue" becomes natural resumption, not a separate invocation). The two cold
agents (`review-gate`, `verifier`) stay agents.

**Why the architecture is safe:** `brain-walk.py --state <any>` already starts anywhere (verified). So
"multi-entry" is not a stepping-engine rewrite — it is (a) adding the two missing regions to the graph,
(b) marking the 4 entry nodes, (c) extracting the engine, (d) renames.

**Two-repo / pre-commit reality (from cold review — do not skip):**
- Skills live in **`personal/agents`** (the `brain/` tree there is currently **untracked** — `git mv`
  errors on untracked files). `flow.toml`/`flow.json`/`bin/*.py` live in **`aav-brain`**. Registration
  is nix-generated from **`personal/home/home.nix`** (`brainSkills` list → fans to `.claude`/`.agents`/
  `.codex`). **Three repos + a nix generation**, not one. Every "rename skill + re-point flow owner" is
  therefore a **cross-repo** pair of commits, not one atomic change.
- The per-phase green gate the staging relies on **does not exist yet**: `brain-flow.py --check`
  validates transitions/reachability/boundary but **never checks that an `owner` resolves to a real
  skill**. Until Phase 0 adds that check, a stale owner passes green and the dangling-owner safety story
  is theater. Phase 0 is the precondition that makes every later phase's gate real.

---

## Worked Example FIRST — his motivating scenario, traced end-to-end

`/brain-execute` on a sanctioned plan, cut off mid-build, resumed by saying "continue".

```bash
# ── user: /brain-execute  (a sanctioned plan exists in plans/, regime = execute-through) ──
brain-execute:                                  # THIN entry skill
  STATE=IMPL                                    # execute's entry node into the unified flow
  load brain-meta-drive; run its trampoline from $STATE   # the ONE shared engine (P31)

  brain-meta-drive (the engine, walking flow.json):
    walk IMPL        owner=brain-meta-author-prompt+worker  → dispatch worker → event=implemented
    walk PHASEGATE   owner=brain-review-gate (AGENT)        → event=below_threshold
    walk REMEDIATE   owner=brain-meta-author-prompt+worker  → event=fixed
    walk PHASEGATE   …                                       → event=threshold_met
    walk VERIFY      owner=brain-verifier (AGENT)            → event=more_phases → IMPL (phase 2)
    *** session cut off mid-IMPL phase 2 ***

# ── later, user just types: continue   (NO /brain-continue — that skill no longer exists) ──
brain-execute (re-invoked; its description owns the "continue"/"keep going"/"resume" trigger):
  reconstruct STATE from plans/ + git log/diff + transcript  → STATE=IMPL(phase 2), regime=execute-through
  load brain-meta-drive; run from $STATE

  brain-meta-drive:
    walk IMPL(phase 2) → PHASEGATE → VERIFY → event=last_phase
    walk STYLE   owner=brain-meta-style → walk RECORD owner=brain-meta-commit
    walk CURATE  owner=brain-meta-curate → DONE
```

**What it proves:**
- `brain-execute` is a ~15-line entry skill: *pick entry node → load `brain-meta-drive` → done.* No
  build logic of its own.
- `brain-meta-drive` is the SAME engine `plan`/`review`/`self-refine` use — only the start node differs
  (P31: one trampoline, four callers, never redefined).
- "continue" needs **no new harness mechanism**: it is `brain-execute` re-invoked (its description owns
  the trigger). But reconstruction is **per-entry, not free**: rebuilding `$STATE` for *execute* means
  "find the plan in `plans/` + git diff + transcript" — a *self-refine* cutoff has no `plans/` artifact;
  its state is "which findings did Arpad select" in transcript + `decisions.jsonl`. So **each entry skill
  owns its own region's state-reconstruction; the engine only walks.** `brain-meta-drive` carries the
  walk loop; `brain-execute` carries plan-reconstruction; `brain-self-refine` carries selection-state.
- Node owners are `brain-meta-*` skills the engine loads, or the two cold AGENTS it dispatches.

The same shape for the other three entries (only the entry node changes):

| entry skill | enters flow.json at | traverses to | new region? |
|---|---|---|---|
| `brain-plan` | `RECON` | `SANCTION` (boundary) | no (exists) |
| `brain-execute` | `IMPL` | `DONE` | no (exists) |
| `brain-review` | `REVIEW` (new) | `DONE` | **yes** — cold review → remediate loop |
| `brain-self-refine` | `SR_SCAN` (new) | `DONE` | **yes** — scan→findings→ask→edit→gate→log |

---

## Phases (staged `git mv`, each independently gated)

> Each phase that touches `flow.toml` ends with **rebuild + commit `flow.json`** (it is a committed
> generated artifact in `aav-brain`; skip it and `--check` drift-fails). Cross-repo phases land as
> **separate per-repo commits** (`agents` for skills, `aav-brain` for flow/bin, `home` for nix).

### Phase 0 — precondition: track the tree + make the gate real

**Changes:** (a) commit the untracked `agents/brain/` tree so `git mv` is legal on every later rename.
(b) Add **owner-existence validation** to `brain-flow.py --check`: split each `owner =` on `+` and `:`,
whitelist `worker` / `-` / the two agents (`brain-review-gate`, `brain-verifier`), and error if any
remaining token does not resolve to a skill dir. This is the gate every later phase's "green" claim
depends on — without it the staged-`git mv` safety story is theater.

**Files:** `agents/` (commit `brain/`); `aav-brain/bin/brain-flow.py` (validator).

**Acceptance:** `git ls-files agents/brain/skills | wc -l` > 0; `brain-flow.py --check` now FAILS when an
owner is pointed at a non-existent skill (prove it: temporarily mistype one, see red, revert); green on
the current tree.

### Phase 1 — extract the engine: `brain-continue` → `brain-meta-drive`

**Changes:** `git mv brain-continue brain-meta-drive`. Strip it to the pure trampoline ENGINE: the
EXECUTE-not-read discipline, the `brain-walk` loop, state reconstruction, recall-per-`recall:true`-state,
owner dispatch, next-state-from-data. It takes a start node and walks to a terminal. Remove the
user-facing "supervisor identity"/"continue" framing (that moves to `brain-execute` in Phase 4). In the
SAME phase, re-point the one `flow.toml` owner that names it — `SANCTION owner = "brain-continue"` →
`"brain-meta-drive"` — so the flow never names a dead dir (the dangling-owner lesson, applied per-phase).

**Files:** `agents/brain/skills/brain-continue/` → `brain-meta-drive/`; its `SKILL.md` reworked to an
engine contract; `brain/flow/flow.toml` (SANCTION owner).

**Acceptance:** `brain-meta-drive/SKILL.md` documents the trampoline as a callable engine (start-node
in, walk to terminal); contains no `/brain-continue` user-trigger language; `brain-flow.py --check` green
(no dangling owner).

### Phase 2 — rename the machinery → `brain-meta-*`

**Changes:** `git mv` each of `brain-{intent,recall,style,curate,commit,author-prompt,learn}` →
`brain-meta-*`. In the SAME phase, re-point every `flow.toml` `owner =` (`brain-style:plan` →
`brain-meta-style:plan`, etc.) so the flow never references a missing dir.

**Files:** 7 skill dirs; `brain/flow/flow.toml` (owner strings).

**Acceptance:** `ls agents/brain/skills` shows the `brain-meta-*` names; every `flow.toml` owner
resolves to an existing dir; `brain-flow.py --check` green (rebuild first).

### Phase 3 — `flow.json` multi-entry: add the two missing regions + mark entry nodes

**Changes:** `flow.toml`:
- Add the **self-refine region**: `SR_SCAN → SR_FINDINGS → SR_ASK → SR_EDIT → SR_GATE → SR_LOG → DONE`
  (mirrors this skill's own steps; owners `brain-self-refine` + `brain-meta-*` workers).
- Add the **review region**: `REVIEW → (REMEDIATE loop via review-gate) → VERIFY → DONE` (cold
  multi-lens review of the current diff).
- Mark `kind="entry"` on the 4 entry nodes: `RECON` (plan), `IMPL` (execute), `REVIEW`, `SR_SCAN`.
  (SANCTION owner already re-pointed in Phase 1.)
- **Regime is entry-set, not boundary-set.** Today `brain-meta-drive` infers autonomy from "did we cross
  SANCTION" (ask-first → execute-through). But `review` and `self-refine` reach `DONE` WITHOUT crossing
  SANCTION, and `self-refine` is **ask-first throughout** (its `SR_ASK` is a real pre-sanction ASK gate,
  distinct from post-sanction `BLOCKED`). So add a `regime` field (or per-entry default) on entry nodes;
  the engine reads regime from the entry, not from a boundary crossing. `IMPL`→execute-through;
  `RECON`/`REVIEW`/`SR_SCAN`→ask-first.

**Files:** `brain/flow/flow.toml` (+ rebuilt & committed `flow.json`); `brain-meta-drive/SKILL.md`
(read regime from entry).

**Acceptance:** `brain-flow.py` rebuilds 0 warnings; 4 `kind="entry"` nodes each carry a regime;
`brain-walk.py --state REVIEW` and `--state SR_SCAN` resolve; `flow --check` green (incl. the Phase 0
owner check, now that SR_*/REVIEW owners are `brain-meta-*`).

### Phase 4 — the entry skills: 2 new, 2 thinned, 1 folded

**Changes:**
- **New** `brain-execute/SKILL.md`: thin entry — entry node `IMPL`, loads `brain-meta-drive`, owns the
  "continue/keep going/resume" trigger + the state-reconstruction preamble (lifted from old continue).
- **New** `brain-review/SKILL.md`: thin entry — entry node `REVIEW`, loads `brain-meta-drive`.
- **Thin** `brain-plan` + `brain-self-refine`: keep their artifact/interrogation content, delegate the
  *traversal* to `brain-meta-drive` (they already step it after this plan's own brain-plan hardening).
- **Fold** `brain-kickoff` → into `brain-plan`: **migrate** kickoff's new-project interrogation ritual
  ("what am I missing", no-assumptions seeding) into brain-plan — do not silently drop it — then `git rm`
  kickoff. brain-plan then handles both new + existing work.
- **State-reconstruction is per-entry** (cold-review finding): `brain-execute` reconstructs from `plans/`
  + git; `brain-self-refine` reconstructs its selection-state from transcript + `decisions.jsonl`;
  `brain-meta-drive` reconstructs nothing — it only walks. Don't put a single execute-shaped preamble in
  the engine.

**Files:** new `brain-execute/`, `brain-review/`; edits to `brain-plan/`, `brain-self-refine/`; delete
`brain-kickoff/`.

**Acceptance:** 4 entry skills load; each names its entry node and invokes `brain-meta-drive`;
`/brain-kickoff` gone; the worked example above is reproducible on paper from the skill texts.

### Phase 5 — the sweep: cross-refs (incl. `bin/*.py`), traceability grandfather, nix registration

**Changes:**
- Sweep the ~200 go-forward references across **both repos** (aav-brain ~108, agents ~91): `CONSTITUTION`,
  `INDEX`, sibling `SKILL.md` prose, AND **`bin/*.py` doc strings** (`brain-walk.py`/`brain-flow.py` name
  `brain-continue` in prose — easy to miss, not `.md`). Historical `decisions.jsonl` entries stay immutable.
- **Traceability grandfather (not just a list edit):** the `comm` check compares `decisions.jsonl` (old
  names, immutable) against new names, so every `brain-meta-*` reports "never logged" on day one. Add an
  old→new name map (or seed-entry) so the check measures real drift, not the rename itself. Update the
  hardcoded skill-name list to the new entry/meta split.
- **Registration is a `home.nix` rebuild, not a symlink flip** (cold-review finding): edit the
  `brainSkills` list in `personal/home/home.nix` (fans to `.claude` + `.agents` + `.codex`), then run the
  home-manager rebuild. This is a **third repo** and a system generation — **Arpad runs it, as the true
  last step** (see Open Decision 4). The 11 relative `scripts/` symlinks ride the renames unaffected.

**Files:** `aav-brain/{brain/CONSTITUTION.md,brain/INDEX.md,bin/*.py}`, all `brain-meta-*`/entry
`SKILL.md` cross-refs (agents), `brain-self-refine` traceability list + map, `personal/home/home.nix`.

**Acceptance:** working-tree `grep -rIn` (NOT `git grep` — pre-commit) of the old names returns only
historical `decisions.jsonl` lines across both repos; all gates green incl. Phase 0 owner-check; the
`comm` check lists only legitimately-never-logged skills (grandfather applied); after Arpad's
home-manager rebuild, `.claude`/`.agents`/`.codex` each expose exactly the 4 entries.

---

## Review-Gate Strategy (baked in)

- Each phase gated cold via `brain-review-gate` on its diff: "biggest-bug-to-smallest-nit, be thorough."
- Phases 1, 3, 4 (engine contract, flow regions, new skills) also through the semantic-architecture lens
  — they introduce/move structural units.
- Mechanical gate every phase: `brain-flow.py --check`, `brain-graph.py --check`, `brain-cards.py --check`
  must pass before advancing (the flow/graph must never drift mid-restructure).
- Rename phases add a hard gate: **working-tree `grep -rI`** (the tree is pre-commit; `git grep` is
  blind to it) of the old name returns zero go-forward hits, PLUS the Phase 0 owner-existence check.

---

## Reuse + Minimal-Surface Notes

- **`brain-meta-drive` is the ONE trampoline** (P31). The 4 entries import/load it; none reimplements the
  walk loop. This is the whole point of the engine extraction.
- **`brain-walk.py` is unchanged** — it already starts at any `--state`. No stepping-engine code is
  written; multi-entry is a *graph* change (new regions + entry markers), not an *engine* change.
- **Shared gate regions** (`PHASEGATE`, `VERIFY`, `REMEDIATE`) are reused by execute + review, not
  duplicated per entry (the per-skill-flow-files option was rejected exactly to avoid this).
- **Agents stay agents** (P18): `review-gate`, `verifier` keep cold cleared-context dispatch; no
  `brain-meta-` prefix (different category).
- Net effect: 11 skills → 4 entries + 8 `brain-meta-*` + 2 agents; one deleted (kickoff); one engine
  extracted. Expect net-negative skill-prose LOC (entries get thin).

---

## Open Decisions

1. **What IS `brain-meta-drive` — a loaded skill, or a script + protocol?**
   - **(A, rec)** a `brain-meta-*` SKILL the entry skills load (bag-of-skills, P18). It is prose protocol
     (reconstruct state, dispatch owners, handle gate loops) wrapping the `brain-walk.py` primitive — too
     much judgement to be pure script.
   - (B) fold it entirely into `brain-walk.py` + a one-paragraph shared protocol doc (P19 — recurring op
     is the script). Risk: state-reconstruction + owner-dispatch aren't deterministic enough for a script.

2. **How does "continue" route to `brain-execute` with no `/` command?**
   - **(A, rec)** `brain-execute`'s description CLAIMS the triggers ("continue", "keep going", "pick up
     where we left off", "resume") — exactly as `brain-continue`'s description does today. The model
     auto-loads it on those phrases. No new harness mechanism.
   - (B) a thin always-on hook that maps "continue" → load `brain-execute`. More machinery, no real gain.

3. **Do the `brain-meta-*` skills stay user-invocable?**
   - **(A, rec)** they remain loadable but NOT advertised; the `brain-meta-` prefix signals "don't call
     directly." **Caveat the cold review forced:** since `.claude/skills` is generated from `home.nix`'s
     `brainSkills`, "loadable but unadvertised" still means the engine loads them **by canonical path** —
     if they're dropped from `brainSkills` they aren't symlinked anywhere. So (A) requires path-loading
     regardless (the thing I'd wrongly attributed only to B). Pick (A), load meta by path.
   - (B) actively drop them from `brainSkills` so only 4 entries register. Same path-loading requirement.

4. **Registration ownership — LOCKED: I run the whole thing, incl. the rebuild.** `.claude`/`.agents`/
   `.codex` are generated from `personal/home/home.nix` `brainSkills` + a home-manager rebuild. I do
   Phases 0–5 across all three repos (`agents`, `aav-brain`, `personal/home`) AND run the home-manager
   rebuild as the final step. No handoff.

5. **In-flight backward-compat — LOCKED: one sitting, rebuild last, no transitional symlinks.** The whole
   restructure runs in one session; the live harness keeps the old names until the final rebuild; the
   brain is simply not invoked mid-flight. No throwaway symlinks (option B rejected — not worth the
   cleanup for a single-sitting job).
