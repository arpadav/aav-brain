# plan: fold the self-refine branch into the main tree

status: drafted, not sanctioned. supersedes nothing; the deferral is logged in the decision trace
under "the self-refine branch reaches none of STYLE, VERIFY, RECORD or CURATE".

## the measured problem

`brain-self-refine` runs on a parallel branch that shares no states with the build region:

```
SR_SCAN -> SR_FINDINGS -> SR_ASK -> SR_EDIT -> SR_GATE -> SR_LOG -> DONE
```

reachability from `SR_SCAN`, computed from `flow.json`:

| state | reachable from self-refine |
|---|---|
| STYLE | **no** |
| VERIFY | **no** |
| RECORD | **no** |
| CURATE | **no** |

this is not theoretical. `SR_EDIT` writes code - in the two sessions before this plan it edited
`brainlib.py`, `brain-recall.py`, `brain-flow.py` and `brain-walk.py`. none of it was style-gated,
verified, or commit-prepared BY THE FLOW. it passed only because the operator ran `brain-fmt --gate`
and `brain-lint.py` by hand, which is precisely the "a name is not an instruction" failure the
DOCTRINE gate was added to fix elsewhere.

two states are also duplicates under different names:

| self-refine state | its build-region twin |
|---|---|
| `SR_GATE` - "rebuild what the edit touched; --check must pass" | `VERIFY` - "build/test/bench honestly" |
| `SR_LOG` - "log each decision to the trace" | `CURATE` - "capture corrections; log the decision trace" |

that is a [[principle-31-libraryfy-shared]] violation in the flow rather than in code: the same step
defined twice, free to drift.

## the decision

arpad asked for one tree carrying a **boolean `self_refine` flag**, so the same tree is traversed
differently depending on mode. the concern raised against it - that a mode flag makes the next state
depend on state not present in the data, which is what [[principle-30-deterministic-flow]] forbids -
was put to him and he reaffirmed the boolean. **his call stands, and this plan builds it.**

it is built through the `guard` field, which already exists on every `Transition`, is already
serialised into `flow.json`, and is currently used by **zero** transitions. that keeps the mode
*visible in the data* rather than hidden in the walker: `brain-walk` still answers "given this state,
this event, and this declared mode, what is next" as a pure function. the flag is a declared input,
not ambient state.

## design

### the flag

one boolean, `self_refine`, defaulting to **false** when omitted. it is set once by the entry skill
and passed to every walk call:

```bash
python3 bin/brain-walk.py --state SR_EDIT --on edited --self-refine
```

### the guard

a transition may carry `guard = "self_refine"` or `guard = "!self_refine"`. an unguarded transition
applies in both modes. `Flow.step()` picks the transition whose guard the current mode satisfies.

### what folds

```
before:  SR_EDIT -> SR_GATE -> SR_LOG -> DONE
after:   SR_EDIT -> VERIFY -> STYLE -> RECORD -> CURATE -> DONE
```

every edge after `VERIFY` already exists. the fold is **one new transition and two deleted states**:

| change | detail |
|---|---|
| add | `SR_EDIT --edited--> VERIFY` |
| delete | state `SR_GATE` + its two transitions |
| delete | state `SR_LOG` + its one transition |
| guard | `VERIFY --more_phases--> DOCTRINE` gains `guard = "!self_refine"` - a refine run has no phases |

net: **33 -> 31 states**.

### what does NOT fold, and why

`SR_SCAN`, `SR_FINDINGS`, `SR_ASK` stay. they look like `RECON`, `PLAN` and `ASK` but their contracts
differ: `SR_ASK` is a consent gate whose unselected findings are DROPPED, while `ASK` is a
clarification that returns to `INTENT`. folding those is a second, larger change and is deliberately
out of scope here - arpad's constraint was "i dont want to complicate and make a huge refactor right
now".

### what the shared states mean in refine mode

no new states, only a wider contract in the doc:

- **VERIFY** - in a build, the build/tests/bench. in a refine, the drift gates (`brain-graph`,
  `brain-flow`, `brain-cards`, `compile --check`) plus `brain-lint.py`. the bar is the artifact's own,
  which VERIFY's doc already says.
- **STYLE** - unchanged. on a cards-only refine it is a clean no-op, because `marker_for` returns
  `None` for `.md` and the gate reports nothing.
- **RECORD** - prepares the commit. refine runs currently leave the tree uncommitted; this is a gain,
  not a cost.
- **CURATE** - absorbs `SR_LOG` wholesale; logging decisions to the trace is already its job.

## worked example

a self-refine run that edits `bin/brain-recall.py`, traced end to end:

```bash
eval "$(brain-find --export)"
STATE=SR_SCAN; REFINE=--self-refine

python3 bin/brain-walk.py --state SR_SCAN $REFINE
#   SR_SCAN [entry] owner=brain-self-refine
#   on scanned -> SR_FINDINGS
python3 bin/brain-walk.py --state SR_EDIT --on edited $REFINE
#   SR_EDIT --edited--> VERIFY [gate] owner=brain-verifier
#   DISPATCH ITS OWNER COLD:  Agent(subagent_type='brain-verifier')
python3 bin/brain-walk.py --state VERIFY --on last_phase $REFINE
#   VERIFY --last_phase--> STYLE [gate]
python3 bin/brain-walk.py --state STYLE --on styled $REFINE
#   STYLE --styled--> RECORD [work] owner=brain-meta-commit
python3 bin/brain-walk.py --state CURATE --on learned $REFINE
#   CURATE --learned--> DONE [terminal] owner=brain-learner
```

the same walk WITHOUT the flag, at the one state where the mode matters:

```bash
python3 bin/brain-walk.py --state VERIFY --on more_phases              # build mode
#   VERIFY --more_phases--> DOCTRINE
python3 bin/brain-walk.py --state VERIFY --on more_phases --self-refine
#   brain-walk: no exit from VERIFY on 'more_phases' in self-refine mode
```

that last line is the whole point of the guard: the edge is not merely unused in refine mode, it is
**absent**, and the walker says so rather than routing a refine run into `DOCTRINE`.

## implementation

ordered so each step is independently verifiable.

1. **`brainlib.Flow` / `State` / `Transition`** - `step()` takes a `self_refine: bool` and selects on
   the guard. add `Mode` as a `StrEnum` rather than a bare bool at the boundary, so the guard strings
   `self_refine` / `!self_refine` are parsed once ([[principle-40-idiom-needs-exemplars]] rule 2).
2. **`brain-flow.determinism_warnings`** - key on `(src, on, guard)` instead of `(src, on)`, and add a
   NEW warning: two transitions sharing `(src, on)` whose guards do not partition the modes (both
   unguarded, or the same guard twice) are still ambiguous. without this the fold silently
   reintroduces the non-determinism the guard exists to avoid.
3. **`flow.toml`** - add `SR_EDIT --edited--> VERIFY`; delete `SR_GATE` and `SR_LOG` and their
   transitions; put `guard = "!self_refine"` on `VERIFY --more_phases--> DOCTRINE`.
4. **`brain-walk.py`** - `--self-refine` flag through `Args`/`Flag`, threaded into `step()` and into
   the "no exit" message.
5. **`brain-self-refine` SKILL.md** - set the flag at entry and pass it on every walk call.
6. **`brain-meta-drive` SKILL.md** - the trampoline forwards the flag verbatim; it must not infer it.
7. **docs** - regenerate `DEV_FLOWCHART.md`; the guard should render on the edge label so the two
   modes are legible in the diagram.

## validation

- `brain-flow.py --check` green, `warnings: 0`, and the state count drops 33 -> 31.
- the new determinism warning FIRES on a deliberately-broken pair (add two unguarded `(VERIFY,
  more_phases)` edges, confirm it refuses to build, revert).
- `brain-walk --state VERIFY --on more_phases` differs with and without the flag, as above.
- the flowchart still renders: `mmdc -i flow.mmd -o flow.svg`.
- a real self-refine run reaches `STYLE` and the style gate actually runs without anyone typing it.

## risks

- **the guard is a second way to express routing.** if it spreads past the two or three edges that
  genuinely need it, the flow stops being readable as a plain graph. cap it: a guard is justified only
  where the SAME (src, on) must go to different places. anything else belongs in the state's doc.
- **the entry must set the flag.** a refine run whose entry forgets it traverses build-mode edges. the
  mitigation is that `SR_*` states exist only in refine mode, so a missing flag fails fast at the first
  guarded edge rather than silently doing the wrong thing.
- **`VERIFY` now has two bars.** the state's doc already says the bar is the artifact's own, so this
  is a documentation change, not a semantic one - but it is the place a future reader will trip.
